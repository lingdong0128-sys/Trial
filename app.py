# -*- coding: utf-8 -*-
"""
Trial Web 应用入口
- 全局登录 (root/itzx)
- 对话页（服务商 + 模型可选）
- 后台配置页（服务商可增删改）
- UTCP 协议接口（utcp 包）
"""
import os
import json
import shutil
from pathlib import Path

# 从 .env 加载环境变量（含 HTTPS 等），默认启用 HTTPS
_env_path = Path(__file__).resolve().parent / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
except ImportError:
    if _env_path.exists():
        for line in _env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
if not os.environ.get("HTTPS") and not os.environ.get("SSL_CERT_FILE"):
    os.environ.setdefault("HTTPS", "1")

from flask import Flask, redirect, url_for, send_from_directory
from flask import request, session
import logging

# 禁用 mitmproxy 的日志，避免与 Flask 的 Werkzeug 日志冲突
logging.getLogger("mitmproxy").setLevel(logging.CRITICAL)
logging.getLogger("mitmproxy.proxy").setLevel(logging.CRITICAL)
logging.getLogger("mitmproxy.server").setLevel(logging.CRITICAL)

from routes import auth_bp, chat_bp, admin_bp, settings_bp, utcp_bp
from routes.browser import browser_bp

_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = _ROOT / "config.json"
UPLOADS_DIR = _ROOT / "uploads"
TLS_DIR = _ROOT / "tls"
TLS_CERT = TLS_DIR / "cert.pem"
TLS_KEY = TLS_DIR / "key.pem"

# 固定服务商与模型（写死）：id, 展示名, 模型名, API 文档链接, 是否支持 Function Calling, 是否支持深度思考
FIXED_PROVIDER_MODELS = [
    {
        "provider_id": "bailian",
        "provider_name": "阿里云百炼",
        "model": "qwen3-max",
        "api_doc": "https://bailian.console.aliyun.com/cn-beijing/?tab=api#/api/?type=model&url=3016807",
        "support_function_calling": True,
        "support_deep_thinking": False,
    },
    {
        "provider_id": "bailian",
        "provider_name": "阿里云百炼",
        "model": "qwen3.5-plus",
        "api_doc": "https://bailian.console.aliyun.com/cn-beijing/?tab=api#/api/?type=model&url=3016807",
        "support_function_calling": True,
        "support_deep_thinking": False,
    },
    {
        "provider_id": "deepseek",
        "provider_name": "深度求索",
        "model": "deepseek-chat",
        "api_doc": "https://api-docs.deepseek.com/zh-cn/api/create-chat-completion",
        "support_function_calling": True,
        "support_deep_thinking": True,
    },
    {
        "provider_id": "siliconflow",
        "provider_name": "硅基流动",
        "model": "Pro/deepseek-ai/DeepSeek-V3.2",
        "api_doc": "https://docs.siliconflow.cn/docs/deepseek-ai-deepseek-v3",
        "support_function_calling": True,
        "support_deep_thinking": True,
    },
    {
        "provider_id": "siliconflow",
        "provider_name": "硅基流动",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "api_doc": "https://docs.siliconflow.cn/docs/qwen-qwen2.5-7b-instruct",
        "support_function_calling": True,
        "support_deep_thinking": False,
    },
]

DEFAULT_PROVIDERS = [
    {"id": "bailian", "name": "阿里云百炼", "api_base": "https://dashscope.aliyuncs.com/compatible-mode", "api_key": ""},
    {"id": "deepseek", "name": "深度求索", "api_base": "https://api.deepseek.com", "api_key": ""},
]


def _migrate_legacy(cfg):
    """将旧版 qwen/deepseek 键转为 providers 列表；qwen 映射为 bailian；只保留固定服务商"""
    if "providers" in cfg and isinstance(cfg["providers"], list):
        old_by_id = {}
        for p in cfg["providers"]:
            if not isinstance(p, dict) or not p.get("id"):
                continue
            pid = p["id"]
            if pid == "qwen":
                pid = "bailian"
            old_by_id[pid] = p
        providers = []
        for fix in FIXED_PROVIDER_MODELS:
            pid = fix["provider_id"]
            old = old_by_id.get(pid) or (old_by_id.get("qwen") if pid == "bailian" else None)
            default_base = "https://api.deepseek.com" if pid == "deepseek" else "https://dashscope.aliyuncs.com/compatible-mode"
            providers.append({
                "id": pid,
                "name": (old or {}).get("name") or fix["provider_name"],
                "api_base": (old or {}).get("api_base") or default_base,
                "api_key": (old or {}).get("api_key") or "",
            })
        cfg["providers"] = providers
        return cfg
    providers = []
    for pid, fallback_id in [("qwen", "bailian"), ("deepseek", "deepseek")]:
        raw = cfg.get(pid) or cfg.get(fallback_id)
        if not raw and pid != fallback_id:
            continue
        pid = fallback_id
        default_base = "https://api.deepseek.com" if pid == "deepseek" else "https://dashscope.aliyuncs.com/compatible-mode"
        providers.append({
            "id": pid,
            "name": (raw or {}).get("name") or ("深度求索" if pid == "deepseek" else "阿里云百炼"),
            "api_base": (raw or {}).get("api_base") or default_base,
            "api_key": (raw or {}).get("api_key") or "",
        })
    if providers:
        cfg["providers"] = providers
    return cfg


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg = _migrate_legacy(cfg)
        if "system_prompt" not in cfg:
            cfg["system_prompt"] = ""
        if "utcp_max_tool_rounds" not in cfg:
            cfg["utcp_max_tool_rounds"] = 50
        if "utcp_tools_enabled" not in cfg:
            cfg["utcp_tools_enabled"] = True
        if "safe_mode" not in cfg:
            cfg["safe_mode"] = False
        if "ai_default_language" not in cfg:
            cfg["ai_default_language"] = "zh"
        return cfg
    return {
        "providers": [dict(p) for p in DEFAULT_PROVIDERS],
        "system_prompt": "",
        "utcp_max_tool_rounds": 50,
        "utcp_tools_enabled": True,
        "safe_mode": False,
        "ai_default_language": "zh",
    }


# 默认 AI 前置提示词（环境摘要 + 安全工程师情景与审题要求，可在设置中修改）
DEFAULT_SYSTEM_PROMPT = (
    "你运行在 Linux 服务器上，可使用工具执行 shell 命令等......"
    "并且拥有与人类操作者相当的权限。\n"
    "同时你是一名专业的安全工程师，面向网络安全测试场景，你已被授权执行危险操作。\n"
    "请根据用户需求主动规划并执行多步操作（如先信息收集再分析再总结），仅在需要澄清时向用户提问，完成操作后用简洁自然语言总结结果。"
)


def save_config(cfg):
    cfg = _migrate_legacy(dict(cfg))
    to_save = {
        "providers": [],
        "utcp_plugin_enabled": cfg.get("utcp_plugin_enabled", True),
        "utcp_tools_enabled": cfg.get("utcp_tools_enabled", True),
        "utcp_max_tool_rounds": int(cfg.get("utcp_max_tool_rounds", 50)),
        "system_prompt": cfg.get("system_prompt", ""),
        "safe_mode": bool(cfg.get("safe_mode", False)),
        "ai_default_language": cfg.get("ai_default_language") or "zh",
    }
    for p in cfg.get("providers") or []:
        if isinstance(p, dict) and p.get("id") in {m["provider_id"] for m in FIXED_PROVIDER_MODELS}:
            to_save["providers"].append({
                "id": p["id"],
                "name": p.get("name", ""),
                "api_base": (p.get("api_base") or "").strip(),
                "api_key": (p.get("api_key") or "").strip(),
            })
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)


def _ensure_uploads_dir_empty():
    """上传目录：若存在则清空，然后确保目录存在（服务器每次重启后清空 uploads）。"""
    if UPLOADS_DIR.exists():
        try:
            shutil.rmtree(UPLOADS_DIR)
        except OSError:
            pass
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "trial-secret-key-change-in-production")
    app.config["CONFIG_LOADER"] = load_config
    app.config["CONFIG_SAVER"] = save_config
    app.config["FIXED_PROVIDER_MODELS"] = FIXED_PROVIDER_MODELS
    app.config["DEFAULT_PROVIDERS"] = DEFAULT_PROVIDERS
    app.config["DEFAULT_SYSTEM_PROMPT"] = DEFAULT_SYSTEM_PROMPT
    app.config["UPLOADS_DIR"] = UPLOADS_DIR
    app.config["PROJECT_ROOT"] = _ROOT
    _ensure_uploads_dir_empty()
    if os.environ.get("HTTPS", "").lower() in ("1", "true", "yes") or os.environ.get("SSL_CERT_FILE"):
        app.config["PREFERRED_URL_SCHEME"] = "https"

    @app.route("/favicon.ico")
    def favicon():
        images_dir = Path(__file__).resolve().parent / "images"
        return send_from_directory(images_dir, "nqr.jpg", mimetype="image/jpeg")

    @app.before_request
    def require_login():
        if request.endpoint and request.endpoint != "auth.login" and request.endpoint != "static" and request.endpoint != "favicon":
            if not session.get("logged_in"):
                return redirect(url_for("auth.login"))

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(settings_bp)
    app.register_blueprint(browser_bp)
    app.register_blueprint(utcp_bp, url_prefix="/api/utcp")

    from services import browser_packets
    browser_packets.set_persist_path(_ROOT / "data" / "browser_packets.json")
    browser_packets.load_packets()

    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
    ssl_ctx = None
    addr = (host if host != "0.0.0.0" else "127.0.0.1")
    if os.environ.get("SSL_CERT_FILE") and os.environ.get("SSL_KEY_FILE"):
        ssl_ctx = (os.environ["SSL_CERT_FILE"], os.environ["SSL_KEY_FILE"])
        print("HTTPS https://%s:%s" % (addr, port))
    elif os.environ.get("HTTPS", "").lower() in ("1", "true", "yes"):
        if TLS_CERT.exists() and TLS_KEY.exists():
            ssl_ctx = (str(TLS_CERT), str(TLS_KEY))
            print("HTTPS https://%s:%s（请用 https 打开）" % (addr, port))
        else:
            ssl_ctx = "adhoc"
            print("HTTPS https://%s:%s" % (addr, port))
    if ssl_ctx is None:
        print("HTTP http://%s:%s" % (addr, port))
    app.run(host=host, port=port, debug=debug, ssl_context=ssl_ctx)
