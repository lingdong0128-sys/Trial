# -*- coding: utf-8 -*-
"""
流量控制工具：UTCP 工具实现，允许 AI 通过 UTCP 协议控制网络流量。
支持添加拦截规则、修改请求头/响应体、阻断请求、重发数据包等功能。
"""
import requests
from services.traffic_rules import traffic_rules
from services.browser_packets import get_packet


def add_traffic_modification(url_regex: str, modification_type: str, data: dict) -> dict:
    """
    添加网络流量修改规则
    
    Args:
        url_regex: 匹配 URL 的正则表达式，例如 'example.com/api'
        modification_type: 修改类型，可选值：
            - 'modify_request_header': 修改请求头
            - 'modify_response_body': 修改响应体
            - 'block_request': 阻断请求
        data: 修改的具体数据：
            - header 修改需包含 'key' 和 'value'
            - body 修改需包含 'old_text' 和 'new_text'
    
    Returns:
        包含执行结果的字典
    """
    try:
        # 验证参数
        if not url_regex:
            return {"success": False, "error": "url_regex 不能为空"}
            
        if modification_type not in ['modify_request_header', 'modify_response_body', 'block_request']:
            return {"success": False, "error": f"不支持的修改类型: {modification_type}"}
        
        # 验证 data 参数
        if modification_type == 'modify_request_header':
            if 'key' not in data or 'value' not in data:
                return {"success": False, "error": "修改请求头需要提供 key 和 value 参数"}
        elif modification_type == 'modify_response_body':
            if 'old_text' not in data or 'new_text' not in data:
                return {"success": False, "error": "修改响应体需要提供 old_text 和 new_text 参数"}
        
        # 添加规则
        rule_id = traffic_rules.add_rule(modification_type, url_regex, data)
        
        return {
            "success": True,
            "message": f"规则已添加，ID: {rule_id}",
            "details": f"当 URL 匹配 '{url_regex}' 时执行 {modification_type}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def clear_traffic_rules() -> dict:
    """
    清除所有流量拦截规则
    
    Returns:
        包含执行结果的字典
    """
    try:
        traffic_rules.clear_rules()
        return {"success": True, "message": "所有拦截规则已清空"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_traffic_rules() -> dict:
    """
    列出所有当前的流量拦截规则
    
    Returns:
        包含规则列表的字典
    """
    try:
        rules = traffic_rules.get_rules()
        return {
            "success": True,
            "message": f"当前共有 {len(rules)} 条规则",
            "data": {"rules": rules, "count": len(rules)}
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def replay_packet(packet_id: str) -> dict:
    """
    重发指定 ID 的数据包
    
    Args:
        packet_id: 要重发的录包 ID
    
    Returns:
        包含重发结果的字典，包括新的响应状态码和响应体预览
    """
    # 1. 获取原数据包
    packet = get_packet(packet_id)
    if not packet:
        return {"error": f"未找到 ID 为 {packet_id} 的数据包"}

    try:
        # 2. 准备请求参数
        method = packet.get("method", "GET")
        url = packet.get("url")
        
        # 过滤掉一些不适合重发的 header (如 Content-Length, Host)
        unsafe_headers = ['content-length', 'host', 'connection', 'upgrade-insecure-requests']
        headers = {k: v for k, v in packet.get("request_headers", {}).items() 
                   if k.lower() not in unsafe_headers}
        
        # 3. 发送请求 (verify=False 忽略 SSL 错误)
        # 注意：这里我们使用 requests 库模拟重发，而不是通过 mitmproxy 内部重放
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=packet.get("request_body_preview"), # 注意：如果是大文件，preview 可能不完整
            verify=False,
            timeout=30
        )

        # 4. 返回结果
        return {
            "status": "success",
            "new_response_status": response.status_code,
            "new_response_body_preview": response.text[:1000] # 截取前1000字符
        }

    except Exception as e:
        return {"error": f"重发失败: {str(e)}"}
