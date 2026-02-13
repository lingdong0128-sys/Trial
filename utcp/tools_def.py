# -*- coding: utf-8 -*-
"""UTCP 工具在 OpenAI 兼容接口中的定义（供对话中模型调用）。"""


def get_openai_tools():
    """
    返回可在 /v1/chat/completions 中传入的 tools 列表（OpenAI 格式）。
    模型可根据用户问题决定是否调用这些工具。
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前日期和时间（默认中国北京时间 UTC+8）。当用户询问现在几点、今天几号、当前时间、星期几、时间戳、现在什么时候时，应调用此工具获取实时数据后再回答。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone_hours": {
                            "type": "number",
                            "description": "可选。时区偏移小时数，如 8 表示北京时间，-5 表示美东。不传则使用北京时间(UTC+8)。",
                        }
                    },
                },
            },
        },
    ]
