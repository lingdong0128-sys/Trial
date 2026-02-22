# -*- coding: utf-8 -*-
"""记录器：录制代理端口展示、录包列表与详情。无内置浏览器，需在本地浏览器中配置代理后使用。"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_file

from services import browser_packets
from services import browser_session

browser_bp = Blueprint("browser", __name__, url_prefix="/")


@browser_bp.route("browser")
def index():
    """原内置浏览器入口，重定向到记录器。"""
    return redirect(url_for("browser.recorder"))


@browser_bp.route("recorder")
def recorder():
    """记录器页面：显示代理端口与 Wireshark 式数据包列表。"""
    return render_template("recorder.html")


@browser_bp.route("api/recorder/proxy", methods=["GET"])
def api_proxy():
    """确保录制代理已启动并返回代理地址与端口，供用户在浏览器中配置使用。"""
    ok, err = browser_session.ensure_proxy_started()
    if not ok:
        return jsonify({"ok": False, "error": err}), 500
    url = browser_session.get_proxy_url()
    port = browser_session.get_proxy_port()
    host = "127.0.0.1"
    return jsonify({
        "ok": True,
        "proxy_url": url,
        "host": host,
        "port": port,
    })


@browser_bp.route("api/browser/packets", methods=["GET", "POST"])
def packets_list_or_clear():
    """GET：返回录包列表（可选 url_contains, limit）；POST：清空录包。"""
    if request.method == "POST":
        browser_packets.clear_packets()
        return jsonify({"ok": True, "message": "已清空"})
    url_contains = request.args.get("url_contains") or ""
    limit = request.args.get("limit", type=int) or 200
    items = browser_packets.list_packets(url_contains=url_contains, limit=limit)
    return jsonify({"packets": items})


@browser_bp.route("api/browser/packets/<packet_id>", methods=["GET"])
def packet_detail(packet_id):
    """返回单条录包详情。"""
    p = browser_packets.get_packet(packet_id)
    if not p:
        return jsonify({"error": "未找到"}), 404
    return jsonify(p)


@browser_bp.route("api/recorder/cert", methods=["GET"])
def download_cert():
    """
    下载 Mitmproxy CA 证书
    用于解密 HTTPS 流量，用户需要将此证书安装到浏览器/系统中并设置为"始终信任"
    """
    cert_path = browser_session.get_mitmproxy_cert_path()
    if not cert_path:
        return jsonify({"error": "证书文件未找到。请先启动代理以生成证书。"}), 404
    
    try:
        return send_file(
            cert_path, 
            as_attachment=True, 
            download_name="mitmproxy-ca-cert.pem",
            mimetype="application/x-pem-file"
        )
    except Exception as e:
        return jsonify({"error": f"证书下载失败: {str(e)}"}), 500
