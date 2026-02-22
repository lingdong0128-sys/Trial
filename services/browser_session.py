# -*- coding: utf-8 -*-
"""录制代理单例：供记录器使用，将浏览器流量录包。无内置浏览器，仅暴露代理端口供本机浏览器配置使用。"""
import threading
import os
from pathlib import Path

_proxy = None
_lock = threading.Lock()


def ensure_proxy_started():
    """启动 Mitmproxy 录制代理（若未启动）。返回 (True, None) 或 (False, error_message)。"""
    global _proxy
    with _lock:
        if _proxy is not None:
            try:
                if _proxy.proxy_url:
                    return (True, None)
            except Exception:
                pass
            try:
                _proxy.stop()
            except Exception:
                pass
            _proxy = None
        try:
            from services.mitm_service import MitmProxyService
            # 使用固定端口 8888，方便用户配置监听端口
            _proxy = MitmProxyService("0.0.0.0", 8888)
            _proxy.start()
            if _proxy.proxy_url:
                return (True, None)
            return (False, "代理启动失败")
        except Exception as e:
            _proxy = None
            return (False, str(e))


def get_proxy_url():
    """当前录制代理地址，如 http://127.0.0.1:xxxx；未启动时返回 None。"""
    with _lock:
        if _proxy is None:
            return None
        try:
            return _proxy.proxy_url
        except Exception:
            return None


def get_proxy_port():
    """当前录制代理端口号；未启动时返回 None。"""
    url = get_proxy_url()
    if not url:
        return None
    try:
        # 从 URL 中提取端口号
        part = url.rstrip("/").split(":")[-1]
        return int(part)
    except (ValueError, IndexError):
        return None


def get_mitmproxy_cert_path():
    """
    获取 Mitmproxy CA 证书路径
    
    Returns:
        证书文件的完整路径，如果不存在则返回 None
    """
    # Mitmproxy 默认在用户目录下的 .mitmproxy 文件夹生成证书
    home_dir = Path.home()
    cert_path = home_dir / ".mitmproxy" / "mitmproxy-ca-cert.pem"
    
    if cert_path.exists():
        return str(cert_path)
    return None


def stop_proxy():
    """停止录制代理。"""
    global _proxy
    with _lock:
        p, _proxy = _proxy, None
        if p:
            try:
                p.stop()
            except Exception:
                pass
