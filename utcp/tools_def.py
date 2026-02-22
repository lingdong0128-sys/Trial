# -*- coding: utf-8 -*-
"""UTCP 工具在 OpenAI 兼容接口中的定义（供对话中模型调用）。"""


def get_openai_tools():
    """
    返回可在 /v1/chat/completions 中传入的 tools 列表（OpenAI 格式）。
    模型可根据用户问题决定是否调用这些工具。支持自动化工作流：Shell、文件、目录等。
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前日期和时间（默认中国北京时间 UTC+8）。当用户询问现在几点、今天几号、当前时间、星期几、时间戳时，应调用此工具。",
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
        {
            "type": "function",
            "function": {
                "name": "run_shell",
                "description": "在服务器（Linux）上执行任意 shell 命令。可用于执行系统命令、脚本、查看进程、安装软件、编译、运行程序等。你拥有与人类操作者相当的权限。在对话中调用时，会每 1 分钟根据当前输出由 AI 判断是否卡住，若判定卡住则中止，总时长上限 5 分钟；若需更长运行时间可依赖后台或分步执行。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "要执行的完整 shell 命令，例如：ls -la /tmp、nmap -sT 192.168.1.1、cat /etc/os-release。",
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "可选。超时秒数，默认 1800（30 分钟），最大 14400（4 小时）。安装、编译等耗时操作请显式传入更大值（如 3600、7200）。",
                        },
                        "cwd": {
                            "type": "string",
                            "description": "可选。执行命令时的工作目录路径。",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取服务器上的文件内容（Linux 路径）。路径可为相对项目根或绝对路径（需在项目根下）。用于查看配置、日志、代码等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "文件路径，例如 config.json、/opt/VCSG/Trial/README.md。",
                        },
                        "encoding": {
                            "type": "string",
                            "description": "可选。文件编码，默认 utf-8。",
                        },
                        "max_bytes": {
                            "type": "integer",
                            "description": "可选。最大读取字节数，默认 512KB。",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "向服务器上的文件写入内容（Linux 路径）。若目录不存在会尝试创建。用于创建或修改配置、脚本、代码等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "文件路径。",
                        },
                        "content": {
                            "type": "string",
                            "description": "要写入的完整内容。",
                        },
                        "encoding": {
                            "type": "string",
                            "description": "可选。编码，默认 utf-8。",
                        },
                        "append": {
                            "type": "boolean",
                            "description": "可选。是否追加到文件末尾，默认 false 为覆盖。",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "列出目录下的文件和子目录（Linux 路径）。用于浏览项目结构、查找文件。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "目录路径，默认为项目根目录。",
                        },
                        "include_hidden": {
                            "type": "boolean",
                            "description": "可选。是否包含以 . 开头的隐藏文件/目录，默认 false。",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "从知识库中检索与查询相关的资料片段。知识库位于项目 knowledge 目录（.md/.txt），适用于 CTF、漏洞利用、工具用法等。仅在你认为需要查阅项目内知识库资料时选用，非必须。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索关键词或短语，例如：SQL 注入、SSTI、union select、git 泄漏、某工具名、某漏洞类型。",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "可选。返回最多几条结果，默认 5。",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "preview_web_page",
                "description": "在对话页的实时预览区打开一个网页，供用户查看当前自动化任务涉及的页面。当任务涉及浏览器访问、本地启动的 Web 服务、或需要用户查看某 URL 时调用此工具，便于用户观察任务进度。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "要预览的完整 URL，例如 http://127.0.0.1:8080、https://example.com。必须是 http 或 https。",
                        },
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_browser_packets",
                "description": "列出记录器已录制的 HTTP 数据包（用户将浏览器 HTTP 代理设为记录器页显示的 127.0.0.1:端口 后访问网页的流量会被记录）。可用于分析用户浏览行为、抓包结果。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url_contains": {
                            "type": "string",
                            "description": "可选。只返回 URL 中包含该字符串的录包。",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "可选。返回最多几条，默认 50，最大 200。",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_browser_packet",
                "description": "根据 id 获取记录器某条录包的详情（请求头、请求体预览、响应头、响应体预览）。id 来自 list_browser_packets。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "packet_id": {
                            "type": "string",
                            "description": "录包 id。",
                        },
                    },
                    "required": ["packet_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_traffic_modification",
                "description": "添加网络流量修改规则。可以修改请求头、替换响应内容或阻断请求。当用户需要拦截、修改或阻断特定网站流量时使用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url_regex": {
                            "type": "string",
                            "description": "匹配 URL 的正则表达式，例如 'example.com/api' 或 'baidu.com'",
                        },
                        "modification_type": {
                            "type": "string",
                            "enum": ["modify_request_header", "modify_response_body", "block_request"],
                            "description": "修改类型：modify_request_header（修改请求头）、modify_response_body（修改响应体）、block_request（阻断请求）",
                        },
                        "data": {
                            "type": "object",
                            "description": "修改的具体数据。修改请求头时需包含 'key' 和 'value'；修改响应体时需包含 'old_text' 和 'new_text'；阻断请求时可为空对象。",
                            "properties": {
                                "key": {
                                    "type": "string",
                                    "description": "请求头的键名（仅在修改请求头时使用）"
                                },
                                "value": {
                                    "type": "string",
                                    "description": "请求头的值（仅在修改请求头时使用）"
                                },
                                "old_text": {
                                    "type": "string",
                                    "description": "要替换的原始文本（仅在修改响应体时使用）"
                                },
                                "new_text": {
                                    "type": "string",
                                    "description": "替换后的新文本（仅在修改响应体时使用）"
                                }
                            }
                        },
                    },
                    "required": ["url_regex", "modification_type", "data"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "clear_traffic_rules",
                "description": "清除所有流量拦截规则。当需要重置流量拦截状态时使用。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_traffic_rules",
                "description": "列出所有当前的流量拦截规则。用于查看已设置的拦截规则。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "replay_packet",
                "description": "重发已录制的网络请求（根据 packet_id）。用于测试 API 接口或复现 Bug。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "packet_id": {
                            "type": "string",
                            "description": "要重发的录包 ID"
                        }
                    },
                    "required": ["packet_id"]
                }
            },
        },
    ]
