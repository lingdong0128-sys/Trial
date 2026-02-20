# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
def index():
    """旧路径：重定向到设置下的后台配置"""
    return redirect(url_for("settings.config"))


@admin_bp.route("/api/config", methods=["GET"])
def get_config():
    """返回固定服务商配置（用于前端拉取）"""
    load = current_app.config["CONFIG_LOADER"]
    cfg = load()
    fixed = current_app.config.get("FIXED_PROVIDER_MODELS") or []
    saved = {p["id"]: p for p in (cfg.get("providers") or []) if isinstance(p, dict) and p.get("id")}
    providers = []
    for m in fixed:
        pid = m["provider_id"]
        s = saved.get(pid) or {}
        providers.append({
            "id": pid,
            "name": m["provider_name"],
            "api_base": s.get("api_base") or "",
            "api_key": s.get("api_key") or "",
        })
    return jsonify({"providers": providers})


@admin_bp.route("/api/config", methods=["POST"])
def save_config():
    """保存配置：仅固定服务商的 api_base、api_key；api_key 留空则不覆盖已保存值"""
    data = request.get_json() or {}
    load = current_app.config["CONFIG_LOADER"]
    save = current_app.config["CONFIG_SAVER"]
    cfg = load()
    old_providers = {p["id"]: p for p in (cfg.get("providers") or []) if isinstance(p, dict) and p.get("id")}
    fixed_ids = {m["provider_id"] for m in (current_app.config.get("FIXED_PROVIDER_MODELS") or [])}
    new_list = []
    for p in data.get("providers") or []:
        if not isinstance(p, dict) or not p.get("id") or p.get("id") not in fixed_ids:
            continue
        pid = p.get("id")
        old = old_providers.get(pid) or {}
        fixed_list = current_app.config.get("FIXED_PROVIDER_MODELS") or []
        pname = next((x["provider_name"] for x in fixed_list if x["provider_id"] == pid), pid)
        new_list.append({
            "id": pid,
            "name": pname,
            "api_base": (p.get("api_base") or "").strip(),
            "api_key": (p.get("api_key") or "").strip() or old.get("api_key") or "",
        })
    cfg["providers"] = new_list
    save(cfg)
    return jsonify({"ok": True})
