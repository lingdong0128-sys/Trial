# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context, redirect, url_for, current_app
from services.llm import get_available_models, chat_completion, chat_completion_with_tools, chat_completion_stream


def _model_label(provider_id, model):
    """根据 provider_id 与 model 返回展示用「服务商 - 模型」"""
    for m in get_available_models():
        if m.get("provider_id") == provider_id and m.get("model") == model:
            return m.get("label") or f"{provider_id} - {model}"
    return f"{provider_id} - {model}"
from services.conversation_store import (
    list_conversations,
    get_conversation,
    create_conversation,
    update_conversation,
    delete_conversation,
)
import json

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/utcp")
def utcp_console():
    """旧路径：重定向到设置下的 UTCP 控制台"""
    return redirect(url_for("settings.utcp"))


@chat_bp.route("/")
def index():
    """对话页：先选服务商再选模型，历史对话，流式输出"""
    providers = get_available_models()
    return render_template("chat.html", providers=providers)


@chat_bp.route("/api/models", methods=["GET"])
def api_models():
    """获取可用模型列表及全局配置（是否启用 UTCP 插件）"""
    models = get_available_models()
    cfg = current_app.config["CONFIG_LOADER"]()
    return jsonify({
        "providers": models,
        "utcp_plugin_enabled": cfg.get("utcp_plugin_enabled", True),
    })


@chat_bp.route("/api/conversations", methods=["GET"])
def api_conversations_list():
    """历史对话列表"""
    items = list_conversations()
    return jsonify({"conversations": items})


@chat_bp.route("/api/conversations", methods=["POST"])
def api_conversations_create():
    """新建对话"""
    data = request.get_json() or {}
    title = data.get("title") or "新对话"
    conv = create_conversation(title=title)
    return jsonify(conv)


@chat_bp.route("/api/conversations/<cid>", methods=["GET"])
def api_conversation_get(cid):
    """获取单条对话（含 messages）"""
    conv = get_conversation(cid)
    if not conv:
        return jsonify({"error": "对话不存在"}), 404
    return jsonify(conv)


@chat_bp.route("/api/conversations/<cid>", methods=["PATCH"])
def api_conversation_update(cid):
    """更新对话 title 或 messages"""
    data = request.get_json() or {}
    conv = update_conversation(
        cid,
        title=data.get("title"),
        messages=data.get("messages"),
    )
    if not conv:
        return jsonify({"error": "对话不存在"}), 404
    return jsonify(conv)


@chat_bp.route("/api/conversations/<cid>", methods=["DELETE"])
def api_conversation_delete(cid):
    """删除一条历史对话"""
    if not get_conversation(cid):
        return jsonify({"error": "对话不存在"}), 404
    delete_conversation(cid)
    return jsonify({"ok": True})


@chat_bp.route("/api/chat", methods=["POST"])
def api_chat():
    """对话 API：provider_id + model；完整消息历史；可选 conversation_id、use_utcp_tools、use_deep_thinking"""
    data = request.get_json() or {}
    provider_id = data.get("provider_id")
    model = data.get("model")
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id")
    use_utcp_tools = data.get("use_utcp_tools") is True
    use_deep_thinking = data.get("use_deep_thinking") is True
    if not provider_id or not model or not messages:
        return jsonify({"error": "缺少 provider_id、model 或 messages"}), 400
    try:
        if use_utcp_tools:
            content = chat_completion_with_tools(
                provider_id=provider_id, model=model, messages=messages, use_deep_thinking=use_deep_thinking
            )
        else:
            result = chat_completion(provider_id=provider_id, model=model, messages=messages)
            content = (result.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        model_label = _model_label(provider_id, model)
        if conversation_id:
            conv = get_conversation(conversation_id)
            if conv:
                new_messages = conv.get("messages", []) + [
                    {"role": "user", "content": messages[-1].get("content", "") if messages else ""},
                    {"role": "assistant", "content": content, "model_label": model_label},
                ]
                update_conversation(conversation_id, messages=new_messages)
        else:
            title = (messages[0].get("content") or "新对话")[:50]
            conv = create_conversation(title=title, messages=[
                messages[-2] if len(messages) >= 2 else messages[-1],
                {"role": "assistant", "content": content, "model_label": model_label},
            ])
            conversation_id = conv["id"]
        return jsonify({"choices": [{"message": {"content": content}}], "conversation_id": conversation_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """流式对话：provider_id + model；SSE；可选 use_utcp_tools、use_deep_thinking；完整消息历史与对话持久化"""
    data = request.get_json() or {}
    provider_id = data.get("provider_id")
    model = data.get("model")
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id")
    use_utcp_tools = data.get("use_utcp_tools") is True
    use_deep_thinking = data.get("use_deep_thinking") is True
    if not provider_id or not model or not messages:
        return jsonify({"error": "缺少 provider_id、model 或 messages"}), 400

    def generate():
        full_content = []
        try:
            for chunk in chat_completion_stream(
                provider_id=provider_id, model=model, messages=messages,
                use_utcp_tools=use_utcp_tools, use_deep_thinking=use_deep_thinking,
            ):
                full_content.append(chunk)
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            content = "".join(full_content)
            last_user = messages[-1].get("content", "") if messages else ""
            model_label = _model_label(provider_id, model)
            if conversation_id:
                conv = get_conversation(conversation_id)
                if conv:
                    new_messages = conv.get("messages", []) + [
                        {"role": "user", "content": last_user},
                        {"role": "assistant", "content": content, "model_label": model_label},
                    ]
                    update_conversation(conversation_id, messages=new_messages)
            else:
                title = last_user[:50] if last_user else "新对话"
                conv = create_conversation(title=title, messages=[
                    {"role": "user", "content": last_user},
                    {"role": "assistant", "content": content, "model_label": model_label},
                ])
            yield f"data: {json.dumps({'conversation_id': conv['id'], 'model_label': model_label}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
