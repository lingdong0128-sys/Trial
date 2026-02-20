# -*- coding: utf-8 -*-
"""在应用内执行 UTCP 工具，供对话中模型触发的 tool_call 使用。"""
import json
from pathlib import Path

from . import datetime_tool
from . import shell_tool
from . import file_tool
from services import knowledge_base


def execute_tool(name: str, arguments: dict, llm_judge_callback=None, safe_mode: bool = False, project_root=None, uploads_dir=None) -> str:
    """
    根据工具名称与参数执行对应 UTCP 逻辑，返回 JSON 字符串（作为 tool 消息的 content）。
    若工具不存在或执行异常，返回包含 error 的 JSON 字符串。
    llm_judge_callback: 可选，供 run_shell 使用；(command, stdout, stderr) -> bool，True 表示判定卡住。
    """
    args = arguments if isinstance(arguments, dict) else {}
    try:
        if name == "get_current_time":
            tz = args.get("timezone_hours")
            if tz is not None:
                try:
                    tz = float(tz)
                except (TypeError, ValueError):
                    tz = None
            result = datetime_tool.get_datetime(timezone_hours=tz)
            return json.dumps(result, ensure_ascii=False)

        if name == "run_shell":
            cmd = args.get("command") or ""
            timeout = args.get("timeout_seconds")
            cwd = args.get("cwd")
            result = shell_tool.run_shell(
                command=cmd,
                timeout_seconds=timeout,
                cwd=cwd,
                llm_judge_callback=llm_judge_callback,
            )
            return json.dumps(result, ensure_ascii=False)

        if name == "read_file":
            path = args.get("path") or ""
            encoding = args.get("encoding")
            max_bytes = args.get("max_bytes")
            result = file_tool.read_file(path=path, encoding=encoding, max_bytes=max_bytes)
            return json.dumps(result, ensure_ascii=False)

        if name == "write_file":
            path = args.get("path") or ""
            if safe_mode and project_root is not None:
                try:
                    root = Path(project_root).resolve()
                    uploads = Path(uploads_dir).resolve() if uploads_dir else None
                    p = (root / path.strip()).resolve() if path.strip() and not str(path).strip().startswith("/") else Path(path.strip()).resolve()
                    try:
                        p.relative_to(root)
                    except ValueError:
                        return json.dumps({"success": False, "protocol": "UTCP", "message": "安全模式：不允许写入项目外路径", "data": None}, ensure_ascii=False)
                    if uploads and (p == uploads or str(p).startswith(str(uploads) + "/")):
                        pass
                    else:
                        return json.dumps({"success": False, "protocol": "UTCP", "message": "安全模式已开启：不允许修改项目自身文件（仅允许写入上传目录）。", "data": None}, ensure_ascii=False)
                except Exception:
                    return json.dumps({"success": False, "protocol": "UTCP", "message": "安全模式：路径检查失败", "data": None}, ensure_ascii=False)
            content = args.get("content")
            if content is None:
                content = ""
            encoding = args.get("encoding")
            append = args.get("append") is True
            result = file_tool.write_file(path=path, content=content, encoding=encoding, append=append)
            return json.dumps(result, ensure_ascii=False)

        if name == "list_dir":
            path = args.get("path") or "."
            include_hidden = args.get("include_hidden") is True
            result = file_tool.list_dir(path=path, include_hidden=include_hidden)
            return json.dumps(result, ensure_ascii=False)

        if name == "search_knowledge":
            query = args.get("query") or ""
            top_k = args.get("top_k")
            if top_k is not None:
                try:
                    top_k = max(1, min(20, int(top_k)))
                except (TypeError, ValueError):
                    top_k = 5
            else:
                top_k = 5
            result = knowledge_base.search(query=query, top_k=top_k)
            return json.dumps(result, ensure_ascii=False)

        return json.dumps({"success": False, "error": f"未知工具: {name}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
