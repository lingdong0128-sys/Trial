# -*- coding: utf-8 -*-
"""
LLM 服务：从 config.providers 读取服务商列表，按 provider_id + model 调用。
支持将 UTCP 工具以 OpenAI function 形式传给模型，并处理 model 返回的 tool_calls。
"""
import json
import requests
from flask import current_app

# 禁用 SSL 验证警告（因为我们将忽略 SSL 验证）
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_config():
    return current_app.config["CONFIG_LOADER"]()


def get_available_models():
    """返回固定服务商+模型列表，每项为「服务商 - 模型」选项（含是否支持 Function Calling、深度思考）"""
    fixed = current_app.config.get("FIXED_PROVIDER_MODELS") or []
    return [
        {
            "provider_id": m["provider_id"],
            "model": m["model"],
            "label": f"{m['provider_name']} - {m['model']}",
            "support_function_calling": m.get("support_function_calling", False),
            "support_deep_thinking": m.get("support_deep_thinking", False),
        }
        for m in fixed
    ]


def _openai_style_chat_sync(api_base: str, api_key: str, model: str, messages: list, tools: list = None, extra_body: dict = None) -> dict:
    """非流式请求，返回完整 JSON。与流式拆开，避免含 yield 时整函数变成生成器。"""
    url = (api_base.rstrip("/") + "/v1/chat/completions") if api_base else ""
    no_url_msg = {"choices": [{"message": {"content": "请先在后台配置该服务商的 API 地址与 Key。"}}]}
    if not url:
        return no_url_msg
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if extra_body:
        payload.update(extra_body)
    # 多轮工具调用时请求体与模型推理时间较长，超时设为 300 秒
    # 忽略 SSL 验证（应急方案，用于解决证书问题）
    r = requests.post(url, json=payload, headers=headers, timeout=300, verify=False)
    r.raise_for_status()
    return r.json()


def _openai_style_chat_stream(api_base: str, api_key: str, model: str, messages: list, extra_body: dict = None):
    """流式请求，yield content 块。"""
    url = (api_base.rstrip("/") + "/v1/chat/completions") if api_base else ""
    if not url:
        yield "请先在后台配置该服务商的 API 地址与 Key。"
        return
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "stream": True}
    if extra_body:
        payload.update(extra_body)
    # 多轮工具调用时单次请求可能较久，超时设为 300 秒
    # 忽略 SSL 验证（应急方案，用于解决证书问题）
    r = requests.post(url, json=payload, headers=headers, timeout=300, stream=True, verify=False)
    r.raise_for_status()
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue
        if line.startswith("data: "):
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
                delta = (obj.get("choices") or [{}])[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content
            except json.JSONDecodeError:
                pass


def _openai_style_chat(api_base: str, api_key: str, model: str, messages: list, stream: bool = False, tools: list = None, extra_body: dict = None):
    """OpenAI 兼容接口；stream=True 时 yield content 块；stream=False 时返回 dict。"""
    if stream:
        return _openai_style_chat_stream(api_base, api_key, model, messages, extra_body=extra_body)
    return _openai_style_chat_sync(api_base, api_key, model, messages, tools=tools, extra_body=extra_body)


def _get_provider_config(provider_id: str):
    """从 config.providers 中按 id 查找，返回 (api_base, api_key)"""
    cfg = _get_config()
    providers = cfg.get("providers") or []
    for p in providers:
        if isinstance(p, dict) and p.get("id") == provider_id:
            return (p.get("api_base") or "", p.get("api_key") or "")
    return ("", "")


def chat_completion(provider_id: str, model: str, messages: list) -> dict:
    """按服务商 id + 模型名调用"""
    api_base, api_key = _get_provider_config(provider_id)
    return _openai_style_chat(api_base, api_key, model, messages, stream=False)


def judge_shell_stuck(provider_id: str, model: str, command: str, stdout: str, stderr: str) -> bool:
    """
    根据命令当前输出判断是否已卡住。返回 True 表示应中止（卡住），False 表示可继续执行。
    用于 run_shell 的周期性检查（如每 1 分钟）。
    """
    out = (stdout or "").strip()
    err = (stderr or "").strip()
    combined = (out + "\n--- stderr ---\n" + err).strip()
    if len(combined) > 2500:
        combined = combined[-2500:]
    prompt = (
        "你是一个助手。用户正在服务器上执行一条 shell 命令，命令已运行一段时间，当前已捕获的标准输出和标准错误如下。"
        "请判断：命令是否看起来已卡住（例如长时间无新输出、死循环、重复报错、明显挂起）？"
        "还是仍在正常进行（例如安装进度、下载、编译输出、持续有变化）？"
        "只回复一个词：STOP（判定为卡住需中止）或 CONTINUE（判定为仍在进行）。\n\n"
        "命令：" + (command or "")[:200] + "\n\n当前输出：\n" + (combined or "(暂无输出)")
    )
    try:
        resp = chat_completion(provider_id, model, [{"role": "user", "content": prompt}])
        content = (resp.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        return "STOP" in content.upper()
    except Exception:
        return False


def make_shell_judge_callback(provider_id: str, model: str):
    """返回供 run_shell 使用的判断回调：(command, stdout, stderr) -> True 表示卡住应中止。"""
    def callback(command: str, stdout: str, stderr: str) -> bool:
        return judge_shell_stuck(provider_id, model, command, stdout, stderr)
    return callback


def summarize_conversation_title(provider_id: str, model: str, user_content: str, assistant_content: str) -> str:
    """调用模型生成对话标题，限制 10 字以内。失败返回空字符串。"""
    user_preview = (user_content or "")[:500]
    assistant_preview = (assistant_content or "")[:500]
    prompt = f"""用10个字以内总结以下对话，只输出总结标题，不要引号、不要换行、不要其他解释。

用户：{user_preview}
助手：{assistant_preview}"""
    messages = [{"role": "user", "content": prompt}]
    try:
        result = chat_completion(provider_id, model, messages)
        content = (result.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        title = (content or "").strip().replace("\n", " ").strip()
        if len(title) > 10:
            title = title[:10]
        return title
    except Exception:
        return ""


def chat_completion_with_tools(provider_id: str, model: str, messages: list, max_tool_rounds: int = 50, use_deep_thinking: bool = False) -> str:
    """
    带 UTCP 工具调用的对话（自动化工作流，仿 Cursor）：
    1) 多轮 function call 探索；2) 第一轮执行完后请求「当前情况与计划」；
    3) 继续执行任务；4) 返回综合信息（计划 + 执行结果）。
    """
    from utcp.tools_def import get_openai_tools
    from utcp.tool_executor import execute_tool

    api_base, api_key = _get_provider_config(provider_id)
    tools = get_openai_tools()
    current_messages = list(messages)
    use_tools = True
    extra_body = {"thinking": {"type": "enabled"}} if use_deep_thinking else {}
    shell_judge = make_shell_judge_callback(provider_id, model)
    plan_text = None
    plan_done = False

    for _ in range(max_tool_rounds):
        try:
            resp = _openai_style_chat(
                api_base, api_key, model, current_messages, stream=False,
                tools=tools if use_tools else None,
                extra_body=extra_body if extra_body else None,
            )
        except Exception:
            if use_tools:
                use_tools = False
                resp = _openai_style_chat(
                    api_base, api_key, model, current_messages, stream=False,
                    tools=None, extra_body=extra_body if extra_body else None,
                )
            else:
                raise
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls = msg.get("tool_calls")
        content = (msg.get("content") or "").strip()

        if not tool_calls:
            if plan_text:
                return "【当前情况与计划】\n\n" + plan_text + "\n\n---\n\n【执行结果】\n\n" + (content or "")
            return content or ""

        current_messages.append(msg)
        cfg = _get_config()
        safe_mode = bool(cfg.get("safe_mode", False))
        project_root = current_app.config.get("PROJECT_ROOT")
        project_root = str(project_root) if project_root else None
        uploads_dir = current_app.config.get("UPLOADS_DIR")
        uploads_dir = str(uploads_dir) if uploads_dir else None
        for tc in tool_calls:
            tid = tc.get("id") or ""
            fn = tc.get("function") or {}
            name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = execute_tool(
                name, args,
                llm_judge_callback=shell_judge if name == "run_shell" else None,
                safe_mode=safe_mode, project_root=project_root, uploads_dir=uploads_dir,
            )
            current_messages.append({"role": "tool", "tool_call_id": tid, "content": result})

        if not plan_done:
            plan_done = True
            try:
                plan_text = _request_plan_and_append_messages(
                    api_base, api_key, model, current_messages, extra_body
                )
            except Exception:
                current_messages.append({"role": "user", "content": _PLAN_CONTINUE_USER})

    if plan_text:
        return "【当前情况与计划】\n\n" + plan_text + "\n\n---\n\n【执行结果】\n\n" + (content or "")
    return content or ""


def _tool_result_summary(result_json: str, max_len: int = 280) -> str:
    """从工具返回的 JSON 中提取简短摘要，用于步骤栏展示。"""
    try:
        obj = json.loads(result_json) if isinstance(result_json, str) else result_json
        if not obj.get("success"):
            return obj.get("message") or obj.get("error") or "执行失败"
        data = obj.get("data")
        if data is None:
            return obj.get("message") or "ok"
        if isinstance(data, dict):
            if "stdout" in data and data["stdout"]:
                s = (data["stdout"] or "").strip()
                return s[:max_len] + ("…" if len(s) > max_len else "")
            if "content" in data:
                s = (data.get("content") or "").strip()
                return s[:max_len] + ("…" if len(s) > max_len else "")
            if "summary" in data:
                return (data.get("summary") or "")[:max_len]
            if "entries" in data:
                n = len(data.get("entries") or [])
                return f"共 {n} 项"
            if "results" in data:
                r = data.get("results") or []
                return "检索到 " + str(len(r)) + " 条知识库结果"
        return str(data)[:max_len]
    except Exception:
        return (result_json or "")[:max_len] + ("…" if len(str(result_json or "")) > max_len else "")


# 自动化工作流中「计划阶段」的提示：要求模型先汇报情况与计划，不调用工具
_PLAN_REQUEST_USER = (
    "请用 2～4 句话向用户说明：根据目前已获取的信息，当前情况是什么、以及你接下来的执行计划。"
    "仅输出这段说明，不要调用任何工具。"
)
_PLAN_CONTINUE_USER = "请按计划继续执行。"


def _request_plan_and_append_messages(api_base, api_key, model, current_messages, extra_body) -> str:
    """请求一次仅文本回复（不传 tools），得到「当前情况与计划」；并会把助手回复与继续执行的 user 消息追加到 current_messages。"""
    plan_messages = current_messages + [
        {"role": "user", "content": _PLAN_REQUEST_USER},
    ]
    resp = _openai_style_chat(
        api_base, api_key, model, plan_messages, stream=False,
        tools=None,
        extra_body=extra_body if extra_body else None,
    )
    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    plan_content = (msg.get("content") or "").strip()
    current_messages.append({"role": "user", "content": _PLAN_REQUEST_USER})
    current_messages.append(msg)
    current_messages.append({"role": "user", "content": _PLAN_CONTINUE_USER})
    return plan_content


def chat_completion_stream_with_tool_events(provider_id: str, model: str, messages: list, max_tool_rounds: int = 50, use_deep_thinking: bool = False):
    """
    带 UTCP 工具的工作流流式调用（仿 Cursor）：
    1) 先进行多轮 function call（探索/收集信息）；
    2) 第一轮工具执行完成后，请求模型输出「当前情况与计划」并 yield plan 事件；
    3) 然后继续执行任务（后续 tool_call / tool_result）；
    4) 结束时 yield 最终 content（综合信息）。
    """
    from utcp.tools_def import get_openai_tools
    from utcp.tool_executor import execute_tool

    api_base, api_key = _get_provider_config(provider_id)
    tools = get_openai_tools()
    current_messages = list(messages)
    use_tools = True
    extra_body = {"thinking": {"type": "enabled"}} if use_deep_thinking else {}
    plan_already_shown = False

    for _ in range(max_tool_rounds):
        try:
            resp = _openai_style_chat(
                api_base, api_key, model, current_messages, stream=False,
                tools=tools if use_tools else None,
                extra_body=extra_body if extra_body else None,
            )
        except Exception:
            if use_tools:
                use_tools = False
                resp = _openai_style_chat(
                    api_base, api_key, model, current_messages, stream=False,
                    tools=None, extra_body=extra_body if extra_body else None,
                )
            else:
                raise
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls = msg.get("tool_calls")
        content = (msg.get("content") or "").strip()

        if not tool_calls:
            chunk_size = 8
            for i in range(0, len(content or ""), chunk_size):
                yield {"type": "content", "content": (content or "")[i : i + chunk_size]}
            return

        current_messages.append(msg)
        shell_judge = make_shell_judge_callback(provider_id, model)
        cfg = _get_config()
        safe_mode = bool(cfg.get("safe_mode", False))
        project_root = current_app.config.get("PROJECT_ROOT")
        project_root = str(project_root) if project_root else None
        uploads_dir = current_app.config.get("UPLOADS_DIR")
        uploads_dir = str(uploads_dir) if uploads_dir else None
        for tc in tool_calls:
            tid = tc.get("id") or ""
            fn = tc.get("function") or {}
            name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            args_preview = json.dumps(args, ensure_ascii=False)[:120]
            yield {"type": "tool_call", "tool_call_id": tid, "name": name, "arguments": args, "arguments_preview": args_preview}
            if name == "preview_web_page":
                url = (args.get("url") or "").strip()
                if url.startswith("http://") or url.startswith("https://"):
                    yield {"type": "web_view", "url": url}
            result = execute_tool(
                name, args,
                llm_judge_callback=shell_judge if name == "run_shell" else None,
                safe_mode=safe_mode, project_root=project_root, uploads_dir=uploads_dir,
            )
            summary = _tool_result_summary(result)
            yield {"type": "tool_result", "tool_call_id": tid, "name": name, "result_summary": summary, "result_full": result[:2000] if len(result) > 2000 else result}
            current_messages.append({"role": "tool", "tool_call_id": tid, "content": result})

        # 第一轮工具执行完成后：请求「当前情况与计划」并推给用户，再继续执行
        if not plan_already_shown:
            plan_already_shown = True
            try:
                plan_content = _request_plan_and_append_messages(
                    api_base, api_key, model, current_messages, extra_body
                )
                if plan_content:
                    yield {"type": "plan", "content": plan_content}
            except Exception:
                # 计划请求失败则直接继续下一轮，不阻塞
                current_messages.append({"role": "user", "content": _PLAN_CONTINUE_USER})

    yield {"type": "content", "content": ""}


def chat_completion_stream(provider_id: str, model: str, messages: list, use_utcp_tools: bool = False, use_deep_thinking: bool = False, max_tool_rounds: int = 50):
    """
    流式调用。若 use_utcp_tools 为 True，yield 的为事件对象 {type, ...}（tool_call / tool_result / content），
    供前端展示步骤栏与最终内容；否则 yield 纯 content 字符串块。
    """
    if use_utcp_tools:
        for ev in chat_completion_stream_with_tool_events(provider_id, model, messages, max_tool_rounds=max_tool_rounds, use_deep_thinking=use_deep_thinking):
            yield ev
        return
    api_base, api_key = _get_provider_config(provider_id)
    extra_body = {"thinking": {"type": "enabled"}} if use_deep_thinking else None
    for chunk in _openai_style_chat(api_base, api_key, model, messages, stream=True, extra_body=extra_body):
        yield chunk
