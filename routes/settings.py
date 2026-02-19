# -*- coding: utf-8 -*-
"""设置聚合页：左侧栏切换 API信息、全局配置、UTCP 控制台、关于我们。"""
import shutil
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
    """全局配置：API 配置检测、UTCP 插件、自动化工作流、最大轮次、AI 前置提示词"""
    load = current_app.config["CONFIG_LOADER"]
    cfg = load()
    utcp_enabled = cfg.get("utcp_plugin_enabled", True)
    utcp_tools_enabled = cfg.get("utcp_tools_enabled", True)
    utcp_max_tool_rounds = int(cfg.get("utcp_max_tool_rounds", 50))
    system_prompt = cfg.get("system_prompt", "")
    safe_mode = bool(cfg.get("safe_mode", False))
    ai_default_language = cfg.get("ai_default_language") or "zh"
    from app import DEFAULT_SYSTEM_PROMPT
    return render_template(
        "settings_global.html",
        utcp_plugin_enabled=utcp_enabled,
        utcp_tools_enabled=utcp_tools_enabled,
        utcp_max_tool_rounds=utcp_max_tool_rounds,
        system_prompt=system_prompt,
        default_system_prompt=DEFAULT_SYSTEM_PROMPT,
        safe_mode=safe_mode,
        ai_default_language=ai_default_language,
    )


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


@settings_bp.route("/global/api/utcp-tools", methods=["GET", "POST"])
def global_utcp_tools():
    """GET 返回自动化工作流开关与最大轮次；POST 设置（body: {"utcp_tools_enabled": bool, "utcp_max_tool_rounds": int}）"""
    load = current_app.config["CONFIG_LOADER"]
    save = current_app.config["CONFIG_SAVER"]
    if request.method == "GET":
        cfg = load()
        return jsonify({
            "utcp_tools_enabled": cfg.get("utcp_tools_enabled", True),
            "utcp_max_tool_rounds": int(cfg.get("utcp_max_tool_rounds", 50)),
        })
    data = request.get_json() or {}
    cfg = load()
    if "utcp_tools_enabled" in data:
        cfg["utcp_tools_enabled"] = bool(data["utcp_tools_enabled"])
    if "utcp_max_tool_rounds" in data:
        try:
            n = int(data["utcp_max_tool_rounds"])
            cfg["utcp_max_tool_rounds"] = max(1, min(200, n))
        except (TypeError, ValueError):
            pass
    save(cfg)
    return jsonify({
        "ok": True,
        "utcp_tools_enabled": cfg.get("utcp_tools_enabled", True),
        "utcp_max_tool_rounds": int(cfg.get("utcp_max_tool_rounds", 50)),
    })


@settings_bp.route("/global/api/safe-mode", methods=["GET", "POST"])
def global_safe_mode():
    """GET 返回安全模式；POST 设置（body: {"safe_mode": true/false}）"""
    load = current_app.config["CONFIG_LOADER"]
    save = current_app.config["CONFIG_SAVER"]
    if request.method == "GET":
        cfg = load()
        return jsonify({"safe_mode": bool(cfg.get("safe_mode", False))})
    data = request.get_json() or {}
    cfg = load()
    cfg["safe_mode"] = bool(data.get("safe_mode", False))
    save(cfg)
    return jsonify({"ok": True, "safe_mode": cfg["safe_mode"]})


@settings_bp.route("/global/api/ai-default-language", methods=["GET", "POST"])
def global_ai_default_language():
    """GET 返回 AI 默认语言；POST 设置（body: {"ai_default_language": "zh"|"en"|"auto"}）"""
    load = current_app.config["CONFIG_LOADER"]
    save = current_app.config["CONFIG_SAVER"]
    if request.method == "GET":
        cfg = load()
        return jsonify({"ai_default_language": cfg.get("ai_default_language") or "zh"})
    data = request.get_json() or {}
    val = (data.get("ai_default_language") or "zh").strip() or "zh"
    if val not in ("zh", "en", "auto"):
        val = "zh"
    cfg = load()
    cfg["ai_default_language"] = val
    save(cfg)
    return jsonify({"ok": True, "ai_default_language": cfg["ai_default_language"]})


@settings_bp.route("/global/api/system-prompt", methods=["GET", "POST"])
def global_system_prompt():
    """GET 返回当前 AI 前置提示词；POST 保存（body: {"system_prompt": "..."}）"""
    load = current_app.config["CONFIG_LOADER"]
    save = current_app.config["CONFIG_SAVER"]
    if request.method == "GET":
        cfg = load()
        return jsonify({"system_prompt": cfg.get("system_prompt", "")})
    data = request.get_json() or {}
    system_prompt = data.get("system_prompt")
    if system_prompt is None:
        system_prompt = ""
    else:
        system_prompt = str(system_prompt).strip()
    cfg = load()
    cfg["system_prompt"] = system_prompt
    save(cfg)
    return jsonify({"ok": True, "system_prompt": cfg["system_prompt"]})


@settings_bp.route("/global/api/clear-uploads", methods=["POST"])
def global_clear_uploads():
    """清空 uploads 上传目录（手动清空）。"""
    uploads_dir = Path(current_app.config["UPLOADS_DIR"])
    try:
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        return jsonify({"ok": True, "message": "已清空上传文件"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@settings_bp.route("/knowledge")
def knowledge():
    """知识库状态页：查看 knowledge 目录下的文件与块数"""
    from services.knowledge_base import get_status
    status = get_status()
    return render_template("settings_knowledge.html", **status)


@settings_bp.route("/knowledge/api/status")
def knowledge_api_status():
    """API：返回知识库状态（JSON）"""
    from services.knowledge_base import get_status
    return jsonify(get_status())


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
