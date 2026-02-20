# -*- coding: utf-8 -*-
"""UTCP 服务健康检查。"""
from flask import jsonify

from .blueprint import utcp_bp


@utcp_bp.route("/health", methods=["GET"])
def utcp_health():
    """UTCP 服务健康检查"""
    return jsonify({"status": "ok", "protocol": "UTCP"})
