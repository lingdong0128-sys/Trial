# -*- coding: utf-8 -*-
"""在应用内执行 UTCP 工具，供对话中模型触发的 tool_call 使用。"""
import json

from . import datetime_tool


def execute_tool(name: str, arguments: dict) -> str:
    """
    根据工具名称与参数执行对应 UTCP 逻辑，返回 JSON 字符串（作为 tool 消息的 content）。
    若工具不存在或执行异常，返回包含 error 的 JSON 字符串。
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
        return json.dumps({"success": False, "error": f"未知工具: {name}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
