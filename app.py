# -*- coding: utf-8 -*-
"""
Trial Web 应用入口
- 全局登录 (root/itzx)
- 对话页（服务商 + 模型可选）
- 后台配置页（服务商可增删改）
- UTCP 协议占位接口
"""
import os
import json
from pathlib import Path

from flask import Flask, redirect, url_for, send_from_directory
from flask import request, session

from routes import auth_bp, chat_bp, admin_bp, utcp_bp

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULT_PROVIDERS = [
    {"id": "qwen", "name": "通义千问 (QWEN)", "api_base": "", "api_key": "", "models": ["qwen-turbo"]},
    {"id": "deepseek", "name": "DeepSeek", "api_base": "https://api.deepseek.com", "api_key": "", "models": ["deepseek-chat"]},
]


def _migrate_legacy(cfg):
    """将旧版 qwen/deepseek 键转为 providers 列表"""
    if "providers" in cfg and isinstance(cfg["providers"], list):
        return cfg
    providers = []
    for pid, default_name in [("qwen", "通义千问 (QWEN)"), ("deepseek", "DeepSeek")]:
        raw = cfg.get(pid)
        if not raw:
            continue
        models = raw.get("models")
        if not models and raw.get("model"):
            models = [raw["model"]]
        if not models:
            models = ["qwen-turbo"] if pid == "qwen" else ["deepseek-chat"]
        providers.append({
            "id": pid,
            "name": raw.get("name") or default_name,
            "api_base": raw.get("api_base") or ("" if pid == "qwen" else "https://api.deepseek.com"),
            "api_key": raw.get("api_key") or "",
            "models": models if isinstance(models, list) else [m.strip() for m in str(models).split(",") if m.strip()],
        })
    if providers:
        cfg["providers"] = providers
    return cfg


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return _migrate_legacy(cfg)
    return {"providers": [dict(p) for p in DEFAULT_PROVIDERS]}


def save_config(cfg):
    cfg = _migrate_legacy(dict(cfg))
    to_save = {"providers": cfg.get("providers") or []}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "trial-secret-key-change-in-production")
    app.config["CONFIG_LOADER"] = load_config
    app.config["CONFIG_SAVER"] = save_config

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
    app.register_blueprint(utcp_bp, url_prefix="/api/utcp")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
