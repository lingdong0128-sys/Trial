# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from services.llm import get_available_models, chat_completion, chat_completion_stream
from services.conversation_store import (
    list_conversations,
    get_conversation,
    create_conversation,
    update_conversation,
    delete_conversation,
)
import json

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/")
def index():
    """对话页：先选服务商再选模型，历史对话，流式输出"""
    providers = get_available_models()
    return render_template("chat.html", providers=providers)


@chat_bp.route("/api/models", methods=["GET"])
def api_models():
    """获取可用模型列表：按服务商分组（先选服务商再选模型）"""
    providers = get_available_models()
    return jsonify({"providers": providers})


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
    """对话 API：provider_id + model；完整消息历史；可选 conversation_id"""
    data = request.get_json() or {}
    provider_id = data.get("provider_id")
    model = data.get("model")
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id")
    if not provider_id or not model or not messages:
        return jsonify({"error": "缺少 provider_id、model 或 messages"}), 400
    try:
        result = chat_completion(provider_id=provider_id, model=model, messages=messages)
        content = (result.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        # 持久化到对话：有 conversation_id 则追加，否则新建
        if conversation_id:
            conv = get_conversation(conversation_id)
            if conv:
                new_messages = conv.get("messages", []) + [
                    {"role": "user", "content": messages[-1].get("content", "") if messages else ""},
                    {"role": "assistant", "content": content},
                ]
                update_conversation(conversation_id, messages=new_messages)
        else:
            title = (messages[0].get("content") or "新对话")[:50]
            conv = create_conversation(title=title, messages=[
                messages[-2] if len(messages) >= 2 else messages[-1],
                {"role": "assistant", "content": content},
            ])
            conversation_id = conv["id"]
        return jsonify({"choices": [{"message": {"content": content}}], "conversation_id": conversation_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """流式对话：provider_id + model；SSE；完整消息历史与对话持久化"""
    data = request.get_json() or {}
    provider_id = data.get("provider_id")
    model = data.get("model")
    messages = data.get("messages", [])
    conversation_id = data.get("conversation_id")
    if not provider_id or not model or not messages:
        return jsonify({"error": "缺少 provider_id、model 或 messages"}), 400

    def generate():
        full_content = []
        try:
            for chunk in chat_completion_stream(provider_id=provider_id, model=model, messages=messages):
                full_content.append(chunk)
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            # 持久化
            content = "".join(full_content)
            last_user = messages[-1].get("content", "") if messages else ""
            if conversation_id:
                conv = get_conversation(conversation_id)
                if conv:
                    new_messages = conv.get("messages", []) + [
                        {"role": "user", "content": last_user},
                        {"role": "assistant", "content": content},
                    ]
                    update_conversation(conversation_id, messages=new_messages)
            else:
                title = last_user[:50] if last_user else "新对话"
                conv = create_conversation(title=title, messages=[
                    {"role": "user", "content": last_user},
                    {"role": "assistant", "content": content},
                ])
                yield f"data: {json.dumps({'conversation_id': conv['id']}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
