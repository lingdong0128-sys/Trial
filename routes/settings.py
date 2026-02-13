# -*- coding: utf-8 -*-
"""设置聚合页：左侧栏切换 API信息、全局配置、UTCP 控制台、关于我们。"""
from pathlib import Path
from flask import Blueprint, redirect, url_for, render_template, current_app, request, jsonify

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/")
def index():
    """进入设置时默认打开 全局配置"""
    return redirect(url_for("settings.global_config"))


@settings_bp.route("/config")
def config():
    """API信息：固定服务商 API 配置"""
    load = current_app.config["CONFIG_LOADER"]
    cfg = load()
    fixed = current_app.config.get("FIXED_PROVIDER_MODELS") or []
    saved = {p["id"]: p for p in (cfg.get("providers") or []) if isinstance(p, dict) and p.get("id")}
    providers = []
    for m in fixed:
        pid = m["provider_id"]
        s = saved.get(pid) or {}
        providers.append({
            "provider_id": pid,
            "provider_name": m["provider_name"],
            "model": m["model"],
            "api_doc": m.get("api_doc", ""),
            "api_base": s.get("api_base") or "",
            "api_key": s.get("api_key") or "",
        })
    return render_template("settings_config.html", providers=providers)


@settings_bp.route("/global")
def global_config():
    """全局配置：API 配置检测、是否启用 UTCP 插件"""
    load = current_app.config["CONFIG_LOADER"]
    cfg = load()
    utcp_enabled = cfg.get("utcp_plugin_enabled", True)
    return render_template("settings_global.html", utcp_plugin_enabled=utcp_enabled)


@settings_bp.route("/global/api/check", methods=["POST"])
def global_api_check():
    """检测各服务商 API 配置是否可用"""
    from services.llm import _get_provider_config, _openai_style_chat_sync
    load = current_app.config["CONFIG_LOADER"]
    cfg = load()
    fixed = current_app.config.get("FIXED_PROVIDER_MODELS") or []
    saved = {p["id"]: p for p in (cfg.get("providers") or []) if isinstance(p, dict) and p.get("id")}
    results = []
    for m in fixed:
        pid = m["provider_id"]
        s = saved.get(pid) or {}
        api_base = s.get("api_base") or ""
        api_key = s.get("api_key") or ""
        label = f"{m['provider_name']} - {m['model']}"
        if not api_base or not api_key:
            results.append({"label": label, "ok": False, "message": "未配置 API Base 或 API Key"})
            continue
        try:
            resp = _openai_style_chat_sync(
                api_base, api_key, m["model"],
                [{"role": "user", "content": "hi"}],
                tools=None, extra_body=None,
            )
            err = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
            if "请先" in err:
                results.append({"label": label, "ok": False, "message": err})
            else:
                results.append({"label": label, "ok": True, "message": "连接正常"})
        except Exception as e:
            results.append({"label": label, "ok": False, "message": str(e)})
    return jsonify({"results": results})


@settings_bp.route("/global/api/utcp", methods=["GET", "POST"])
def global_utcp_toggle():
    """GET 返回是否启用 UTCP；POST 设置是否启用（body: {"utcp_plugin_enabled": true/false}）"""
    load = current_app.config["CONFIG_LOADER"]
    save = current_app.config["CONFIG_SAVER"]
    if request.method == "GET":
        cfg = load()
        return jsonify({"utcp_plugin_enabled": cfg.get("utcp_plugin_enabled", True)})
    data = request.get_json() or {}
    enabled = data.get("utcp_plugin_enabled", True)
    cfg = load()
    cfg["utcp_plugin_enabled"] = bool(enabled)
    save(cfg)
    return jsonify({"ok": True, "utcp_plugin_enabled": cfg["utcp_plugin_enabled"]})


@settings_bp.route("/utcp")
def utcp():
    """UTCP 控制台"""
    return render_template("settings_utcp.html")


@settings_bp.route("/about")
def about():
    """关于我们：渲染 doc/about.md"""
    doc_path = Path(current_app.root_path) / "doc" / "about.md"
    if not doc_path.exists():
        content = "# 关于我们\n\n暂无内容。"
    else:
        content = doc_path.read_text(encoding="utf-8")
    return render_template("settings_about.html", markdown_content=content)
