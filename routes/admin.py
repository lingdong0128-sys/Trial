# -*- coding: utf-8 -*-
import uuid
from flask import Blueprint, render_template, request, jsonify, current_app

admin_bp = Blueprint("admin", __name__)


def _models_list(provider_dict):
    if not provider_dict:
        return []
    if isinstance(provider_dict.get("models"), list):
        return provider_dict["models"]
    if provider_dict.get("model"):
        return [provider_dict["model"]]
    return []


@admin_bp.route("/")
def index():
    """后台配置页：服务商列表，可增删改名称与模型"""
    load = current_app.config["CONFIG_LOADER"]
    cfg = load()
    providers = cfg.get("providers") or []
    # 兼容旧版：无 providers 时从 qwen/deepseek 构造
    if not providers:
        for pid, name in [("qwen", "通义千问 (QWEN)"), ("deepseek", "DeepSeek")]:
            c = cfg.get(pid) or {}
            providers.append({
                "id": pid,
                "name": c.get("name") or name,
                "api_base": c.get("api_base") or "",
                "api_key": c.get("api_key") or "",
                "models": _models_list(c) or (["qwen-turbo"] if pid == "qwen" else ["deepseek-chat"]),
            })
    return render_template("admin.html", providers=providers)


@admin_bp.route("/api/config", methods=["GET"])
def get_config():
    load = current_app.config["CONFIG_LOADER"]
    cfg = load()
    providers = cfg.get("providers") or []
    for p in providers:
        if isinstance(p, dict) and "models" not in p:
            p["models"] = _models_list(p)
    return jsonify({"providers": providers})


@admin_bp.route("/api/config", methods=["POST"])
def save_config():
    """保存配置：providers 数组；每个 provider 的 api_key 留空则不覆盖"""
    data = request.get_json() or {}
    load = current_app.config["CONFIG_LOADER"]
    save = current_app.config["CONFIG_SAVER"]
    cfg = load()
    old_providers = {p["id"]: p for p in (cfg.get("providers") or []) if isinstance(p, dict) and p.get("id")}
    new_list = []
    for p in data.get("providers") or []:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        pid = p.get("id")
        old = old_providers.get(pid) or {}
        entry = {
            "id": pid,
            "name": (p.get("name") or old.get("name") or pid).strip(),
            "api_base": (p.get("api_base") or "").strip(),
            "api_key": (p.get("api_key") or "").strip() or old.get("api_key") or "",
            "models": p.get("models") if isinstance(p.get("models"), list) else (old.get("models") or []),
        }
        if not entry["models"]:
            entry["models"] = ["default"]
        new_list.append(entry)
    cfg["providers"] = new_list
    save(cfg)
    return jsonify({"ok": True})
