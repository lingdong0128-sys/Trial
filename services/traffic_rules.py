# -*- coding: utf-8 -*-
"""
流量规则管理器：单例模式，用于存储和管理 AI 下发的流量拦截规则。
规则类型包括：修改请求头、修改响应体、阻断请求等。
"""
import re
from typing import List, Dict, Optional


class TrafficRuleManager:
    """流量规则管理器单例类"""
    
    _instance = None
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super(TrafficRuleManager, cls).__new__(cls)
            cls._instance.rules = []
        return cls._instance

    def add_rule(self, rule_type: str, url_regex: str, action_data: dict) -> str:
        """
        添加新的流量拦截规则
        
        Args:
            rule_type: 规则类型，如 'modify_request_header', 'modify_response_body', 'block_request' 等
            url_regex: 匹配 URL 的正则表达式
            action_data: 规则执行所需的具体数据
            
        Returns:
            新规则的 ID
        """
        rule = {
            "id": str(len(self.rules) + 1),
            "type": rule_type,
            "regex": url_regex,
            "data": action_data,
            "enabled": True
        }
        self.rules.append(rule)
        return rule["id"]

    def get_rules(self) -> List[Dict]:
        """获取所有规则列表"""
        return self.rules

    def clear_rules(self):
        """清空所有规则"""
        self.rules = []

    def match_rules(self, flow, phase: str) -> List[Dict]:
        """
        根据请求/响应匹配适用的规则
        
        Args:
            flow: mitmproxy 的 HTTPFlow 对象
            phase: 阶段标识，'request' 或 'response'
            
        Returns:
            匹配的规则列表
        """
        matched = []
        url = flow.request.pretty_url
        
        for rule in self.rules:
            if not rule["enabled"]:
                continue
            
            # 根据阶段过滤规则类型
            if phase == 'request' and 'response' in rule['type']:
                continue
            if phase == 'response' and 'request' in rule['type']:
                continue

            # 使用正则表达式匹配 URL
            try:
                if re.search(rule["regex"], url):
                    matched.append(rule)
            except re.error:
                # 正则表达式错误，跳过该规则
                pass
                
        return matched


# 创建全局单例实例
traffic_rules = TrafficRuleManager()
