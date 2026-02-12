# -*- coding: utf-8 -*-
"""
UTCP 协议调用端口占位：提供查询应用等占位接口，便于后续接入真实 UTCP 实现。
"""
from flask import Blueprint, request, jsonify

utcp_bp = Blueprint("utcp", __name__)


def query_application(app_id: str = None, **kwargs) -> dict:
    """
    占位：通过 UTCP 协议查询应用的接口。
    后续可在此接入真实 UTCP 客户端（如 socket/HTTP 调用模型服务）。
    """
    return {
        "success": True,
        "protocol": "UTCP",
        "message": "占位接口：UTCP 查询应用尚未接入",
        "app_id": app_id,
        "data": None,
    }


@utcp_bp.route("/query", methods=["GET", "POST"])
def utcp_query():
    """UTCP 查询应用 - 占位端点"""
    if request.method == "GET":
        app_id = request.args.get("app_id")
    else:
        data = request.get_json() or request.form or {}
        app_id = data.get("app_id") if isinstance(data, dict) else None
    result = query_application(app_id=app_id)
    return jsonify(result)


@utcp_bp.route("/health", methods=["GET"])
def utcp_health():
    """UTCP 服务健康检查占位"""
    return jsonify({"status": "ok", "protocol": "UTCP", "message": "占位"})
