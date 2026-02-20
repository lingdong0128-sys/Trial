# -*- coding: utf-8 -*-
import re
import uuid
from pathlib import Path

from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context, redirect, url_for, current_app
from services.llm import get_available_models, chat_completion, chat_completion_with_tools, chat_completion_stream, summarize_conversation_title


def _safe_filename(name):
    """保留扩展名，文件名仅保留安全字符。"""
    name = name or "file"
    if "/" in name or "\\" in name:
        name = name.replace("\\", "/").split("/")[-1]
    safe = re.sub(r"[^\w.\-]", "_", name)
    return safe or "file"


def _inject_attachment_paths(messages, attachment_paths):
    """若有上传文件路径，在最后一条用户消息前注入说明，便于模型用 read_file 读取。"""
    if not attachment_paths or not messages:
        return messages
    paths = [p for p in attachment_paths if p and isinstance(p, str)]
    if not paths:
        return messages
    prefix = "【用户在本轮上传了以下文件，路径相对于项目根，可使用 read_file 工具读取】\n" + "\n".join(paths) + "\n\n"
    out = list(messages)
    for i in range(len(out) - 1, -1, -1):
        if out[i].get("role") == "user":
            out[i] = dict(out[i])
            out[i]["content"] = prefix + (out[i].get("content") or "")
            break
    return out


def _model_label(provider_id, model):
    """根据 provider_id 与 model 返回展示用「服务商 - 模型」"""
    for m in get_available_models():
        if m.get("provider_id") == provider_id and m.get("model") == model:
            return m.get("label") or f"{provider_id} - {model}"
    return f"{provider_id} - {model}"
from services.conversation_store import (
    list_conversations,
    get_conversation,
    create_conversation,
    update_conversation,
    delete_conversation,
)
import json

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/utcp")
def utcp_console():
    """旧路径：重定向到设置下的 UTCP 控制台"""
    return redirect(url_for("settings.utcp"))


@chat_bp.route("/")
def index():
    """对话页：先选服务商再选模型，历史对话，流式输出"""
    providers = get_available_models()
    return render_template("chat.html", providers=providers)


@chat_bp.route("/api/models", methods=["GET"])
def api_models():
    """获取可用模型列表及全局配置（UTCP 插件、自动化工作流开关、最大轮次）"""
    models = get_available_models()
    cfg = current_app.config["CONFIG_LOADER"]()
    return jsonify({
        "providers": models,
        "utcp_plugin_enabled": cfg.get("utcp_plugin_enabled", True),
        "utcp_tools_enabled": cfg.get("utcp_tools_enabled", True),
        "utcp_max_tool_rounds": int(cfg.get("utcp_max_tool_rounds", 50)),
    })


@chat_bp.route("/api/conversations", methods=["GET"])
def api_conversations_list():
    """历史对话列表"""
    items = list_conversations()
    return jsonify({"conversations": items})


@chat_bp.route("/api/conversations", methods=["POST"])
def api_conversations_create():
    """新建对话"""
    data = request.get_json() or {}
    title = data.get("title") or "新对话"
    conv = create_conversation(title=title)
    return jsonify(conv)


@chat_bp.route("/api/conversations/<cid>", methods=["GET"])
def api_conversation_get(cid):
    """获取单条对话（含 messages）"""
    conv = get_conversation(cid)
    if not conv:
        return jsonify({"error": "对话不存在"}), 404
    return jsonify(conv)


@chat_bp.route("/api/conversations/<cid>", methods=["PATCH"])
def api_conversation_update(cid):
    """更新对话 title 或 messages"""
    data = request.get_json() or {}
    conv = update_conversation(
        cid,
        title=data.get("title"),
        messages=data.get("messages"),
    )
    if not conv:
        return jsonify({"error": "对话不存在"}), 404
    return jsonify(conv)


@chat_bp.route("/api/conversations/<cid>", methods=["DELETE"])
def api_conversation_delete(cid):
    """删除一条历史对话"""
    if not get_conversation(cid):
        return jsonify({"error": "对话不存在"}), 404
    delete_conversation(cid)
    return jsonify({"ok": True})


@chat_bp.route("/api/upload", methods=["POST"])
def api_upload():
    """上传文件到 uploads 目录，文件类型不限制。返回相对项目根的路径列表。"""
    uploads_dir = Path(current_app.config["UPLOADS_DIR"])
    uploads_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files and request.files.get("file"):
        files = [request.files.get("file")]
    for f in files:
        if not f or not f.filename:
            continue
        name = str(uuid.uuid4()) + "_" + (_safe_filename(f.filename) or "file")
        dest = uploads_dir / name
        try:
            f.save(str(dest))
            paths.append("uploads/" + name)
        except Exception as e:
            return jsonify({"error": "保存失败: " + str(e), "paths": paths}), 500
    return jsonify({"paths": paths})


def _inject_system_prompt(messages, use_utcp_tools):
    """若配置了前置提示词（或启用 UTCP 时使用默认），则在 messages 前插入 system 消息；并附加默认语言约束。"""
    cfg = current_app.config["CONFIG_LOADER"]()
    system_prompt = (cfg.get("system_prompt") or "").strip()
    if use_utcp_tools and not system_prompt:
        system_prompt = (current_app.config.get("DEFAULT_SYSTEM_PROMPT") or "").strip()
    lang = (cfg.get("ai_default_language") or "zh").strip() or "zh"
    if lang == "zh":
        system_prompt = (system_prompt + "\n\n请始终使用中文回复。").strip()
    elif lang == "en":
        system_prompt = (system_prompt + "\n\nPlease always respond in English.").strip()
    if not system_prompt:
        return messages
    return [{"role": "system", "content": system_prompt}] + list(messages)


@chat_bp.route("/api/chat", methods=["POST"])
def api_chat():
    """对话 API：provider_id + model；完整消息历史；可选 conversation_id、use_utcp_tools、use_deep_thinking、attachment_paths"""
    data = request.get_json() or {}
    provider_id = data.get("provider_id")
    model = data.get("model")
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id")
    use_utcp_tools = data.get("use_utcp_tools") is True
    use_deep_thinking = data.get("use_deep_thinking") is True
    attachment_paths = data.get("attachment_paths") or []
    if not provider_id or not model or not messages:
        return jsonify({"error": "缺少 provider_id、model 或 messages"}), 400
    messages = _inject_system_prompt(messages, use_utcp_tools)
    messages = _inject_attachment_paths(messages, attachment_paths)
    cfg = current_app.config["CONFIG_LOADER"]()
    max_tool_rounds = int(cfg.get("utcp_max_tool_rounds", 50))
    try:
        if use_utcp_tools:
            content = chat_completion_with_tools(
                provider_id=provider_id, model=model, messages=messages,
                max_tool_rounds=max_tool_rounds, use_deep_thinking=use_deep_thinking,
            )
        else:
            result = chat_completion(provider_id=provider_id, model=model, messages=messages)
            content = (result.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        model_label = _model_label(provider_id, model)
        last_user = messages[-1].get("content", "") if messages else ""
        if conversation_id:
            conv = get_conversation(conversation_id)
            if conv:
                new_messages = conv.get("messages", []) + [
                    {"role": "user", "content": last_user},
                    {"role": "assistant", "content": content, "model_label": model_label},
                ]
                update_conversation(conversation_id, messages=new_messages)
                if len(new_messages) == 2:
                    summary = summarize_conversation_title(provider_id, model, last_user, content)
                    if summary:
                        update_conversation(conversation_id, title=summary)
        else:
            conv = create_conversation(
                title=(last_user[:50] if last_user else "新对话"),
                messages=[
                    messages[-2] if len(messages) >= 2 else messages[-1],
                    {"role": "assistant", "content": content, "model_label": model_label},
                ],
            )
            conversation_id = conv["id"]
            summary = summarize_conversation_title(provider_id, model, last_user, content)
            if summary:
                update_conversation(conversation_id, title=summary)
        return jsonify({"choices": [{"message": {"content": content}}], "conversation_id": conversation_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """流式对话：provider_id + model；SSE；可选 use_utcp_tools、use_deep_thinking、attachment_paths；完整消息历史与对话持久化"""
    data = request.get_json() or {}
    provider_id = data.get("provider_id")
    model = data.get("model")
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id")
    use_utcp_tools = data.get("use_utcp_tools") is True
    use_deep_thinking = data.get("use_deep_thinking") is True
    attachment_paths = data.get("attachment_paths") or []
    if not provider_id or not model or not messages:
        return jsonify({"error": "缺少 provider_id、model 或 messages"}), 400
    messages = _inject_system_prompt(messages, use_utcp_tools)
    messages = _inject_attachment_paths(messages, attachment_paths)
    cfg = current_app.config["CONFIG_LOADER"]()
    max_tool_rounds = int(cfg.get("utcp_max_tool_rounds", 50))

    last_user = messages[-1].get("content", "") if messages else ""
    model_label = _model_label(provider_id, model)

    def _save_partial(cid, content_parts, steps):
        """流式过程中将当前进度写入对话，便于刷新/切换后恢复（用户消息已在开始时写入，此处只追加或覆盖助手部分）"""
        if not cid:
            return
        conv = get_conversation(cid)
        if not conv:
            return
        partial_content = "".join(content_parts)
        assistant_msg = {"role": "assistant", "content": partial_content, "model_label": model_label}
        if steps:
            assistant_msg["tool_steps"] = list(steps)
        msgs = conv.get("messages", [])
        if msgs and msgs[-1].get("role") == "assistant":
            new_messages = msgs[:-1] + [assistant_msg]
        else:
            new_messages = msgs + [assistant_msg]
        update_conversation(cid, messages=new_messages)

    def generate():
        full_content = []
        tool_steps = []  # 收集本轮工具调用，用于持久化 [{name, arguments_preview, result_summary, result_full}]
        save_interval = 0  # 每累计若干次事件就写库一次，便于刷新后看到进度
        cid = conversation_id
        # 第一轮开始就写入对话历史：新对话立即创建并下发 id，已有对话立即追加用户消息
        if not conversation_id:
            conv = create_conversation(
                title=(last_user[:50] if last_user else "新对话"),
                messages=[{"role": "user", "content": last_user}],
            )
            cid = conv["id"]
            conversation_id = cid
            yield f"data: {json.dumps({'conversation_id': cid}, ensure_ascii=False)}\n\n"
        else:
            conv = get_conversation(conversation_id)
            if conv:
                new_msgs = conv.get("messages", []) + [{"role": "user", "content": last_user}]
                update_conversation(conversation_id, messages=new_msgs)
        try:
            for chunk in chat_completion_stream(
                provider_id=provider_id, model=model, messages=messages,
                use_utcp_tools=use_utcp_tools, use_deep_thinking=use_deep_thinking,
                max_tool_rounds=max_tool_rounds,
            ):
                if use_utcp_tools and isinstance(chunk, dict):
                    ev = chunk
                    if ev.get("type") == "content":
                        full_content.append(ev.get("content") or "")
                        save_interval += 1
                    elif ev.get("type") == "tool_call":
                        tool_steps.append({
                            "name": ev.get("name") or "",
                            "arguments_preview": ev.get("arguments_preview") or "",
                            "result_summary": "",
                            "result_full": "",
                        })
                        save_interval += 1
                    elif ev.get("type") == "tool_result" and tool_steps:
                        summary = (ev.get("result_summary") or ev.get("result_full") or "")[:2000]
                        full_result = (ev.get("result_full") or ev.get("result_summary") or "")[:8000]
                        for st in tool_steps:
                            if not st.get("result_summary") and not st.get("result_full"):
                                st["result_summary"] = summary
                                st["result_full"] = full_result
                                break
                        save_interval += 1
                    if save_interval >= 6:
                        save_interval = 0
                        _save_partial(conversation_id, full_content, tool_steps)
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                else:
                    full_content.append(chunk if isinstance(chunk, str) else "")
                    save_interval += 1
                    if save_interval >= 6:
                        save_interval = 0
                        _save_partial(conversation_id, full_content, tool_steps)
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            content = "".join(full_content)
            assistant_msg = {"role": "assistant", "content": content, "model_label": model_label}
            if tool_steps:
                assistant_msg["tool_steps"] = tool_steps
            conv = get_conversation(cid)
            if conv:
                msgs = conv.get("messages", [])
                if msgs and msgs[-1].get("role") == "assistant":
                    new_messages = msgs[:-1] + [assistant_msg]
                else:
                    new_messages = msgs + [assistant_msg]
                update_conversation(cid, messages=new_messages)
                if len(new_messages) == 2:
                    summary = summarize_conversation_title(provider_id, model, last_user, content)
                    if summary:
                        update_conversation(cid, title=summary)
            yield f"data: {json.dumps({'conversation_id': cid, 'model_label': model_label}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
