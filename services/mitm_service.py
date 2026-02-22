# -*- coding: utf-8 -*-
"""
Mitmproxy 代理服务：基于 Mitmproxy 的流量拦截和录制服务。
支持 HTTPS 解密、实时拦截和修改流量、数据包录制等功能。
"""
import asyncio
import threading
import logging
import re

# 导入数据包存储和规则管理器
from .browser_packets import add_packet
from .traffic_rules import traffic_rules

# 禁用 mitmproxy 的所有日志，避免与 Flask 的 Werkzeug 日志冲突
def _disable_mitmproxy_logging():
    """禁用 mitmproxy 的所有日志记录器"""
    for name in ['mitmproxy', 'mitmproxy.proxy', 'mitmproxy.server', 'mitmproxy.tools']:
        logger = logging.getLogger(name)
        logger.setLevel(logging.CRITICAL)
        logger.propagate = False
        # 移除所有现有的处理器
        logger.handlers = []

_disable_mitmproxy_logging()

# 在禁用日志后再导入 mitmproxy
from mitmproxy import options, http
from mitmproxy.tools.dump import DumpMaster


class AIInterceptorAddon:
    """Mitmproxy 插件：负责流量录制和执行拦截规则"""
    
    # AI API 地址白名单：这些地址不会被拦截，始终放行
    AI_API_WHITELIST = [
        r'dashscope\.aliyuncs\.com',      # 阿里云百炼
        r'api\.deepseek\.com',            # 深度求索
        r'api\.siliconflow\.cn',          # 硅基流动
    ]
    
    def _is_ai_api_request(self, url: str) -> bool:
        """
        检查 URL 是否属于 AI API 白名单
        
        Args:
            url: 请求的完整 URL
            
        Returns:
            True 如果是 AI API 请求，False 否则
        """
        for pattern in self.AI_API_WHITELIST:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def request(self, flow: http.HTTPFlow):
        """
        请求阶段处理
        执行请求阶段的拦截规则（如修改请求头、阻断请求等）
        """
        # 检查是否为 AI API 请求，如果是则放行，不执行任何拦截规则
        if self._is_ai_api_request(flow.request.pretty_url):
            return
        
        # 执行拦截规则（请求阶段）
        matched_rules = traffic_rules.match_rules(flow, 'request')
        for rule in matched_rules:
            if rule['type'] == 'modify_request_header':
                # 修改请求头
                key = rule['data'].get('key')
                value = rule['data'].get('value')
                if key and value:
                    flow.request.headers[key] = value
            elif rule['type'] == 'block_request':
                # 阻断请求
                flow.kill()

    def response(self, flow: http.HTTPFlow):
        """
        响应阶段处理
        执行响应阶段的拦截规则（如修改响应体）并录制数据包
        """
        # 1. 执行拦截规则（响应阶段）
        matched_rules = traffic_rules.match_rules(flow, 'response')
        for rule in matched_rules:
            if rule['type'] == 'modify_response_body':
                # 修改响应体
                old_text = rule['data'].get('old_text')
                new_text = rule['data'].get('new_text')
                if old_text and new_text and flow.response.text:
                    flow.response.text = flow.response.text.replace(old_text, new_text)

        # 2. 录制数据包到现有的存储系统 (browser_packets)
        # 将 mitmproxy 的对象转换为现有 UI 需要的格式
        try:
            req_headers = dict(flow.request.headers) if flow.request.headers else {}
            resp_headers = dict(flow.response.headers) if flow.response and flow.response.headers else {}
            
            # 简单处理 body 预览（限制为前 1024 字节）
            req_body = ""
            resp_body = ""
            
            if flow.request.content:
                req_body = flow.request.content[:1024].decode('utf-8', 'ignore')
                
            if flow.response and flow.response.content:
                resp_body = flow.response.content[:1024].decode('utf-8', 'ignore')

            add_packet(
                method=flow.request.method,
                url=flow.request.pretty_url,
                request_headers=req_headers,
                request_body=req_body,
                response_status=flow.response.status_code if flow.response else 0,
                response_headers=resp_headers,
                response_body=resp_body
            )
        except Exception as e:
            print(f"Error recording packet: {e}")


class MitmProxyService:
    """Mitmproxy 代理服务封装类，管理代理的启动和停止"""
    
    def __init__(self, host="127.0.0.1", port=8080):
        """
        初始化 Mitmproxy 服务
        
        Args:
            host: 监听地址，默认 127.0.0.1
            port: 监听端口，默认 8080
        """
        self.host = host
        self.port = port
        self.master = None
        self.loop = None
        self.thread = None
        self._started = False

    def start(self) -> int:
        """
        启动 Mitmproxy 代理服务
        
        Returns:
            实际监听的端口号
        """
        if self._started:
            return self.port
            
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._started = True
        return self.port

    def _run_loop(self):
        """
        在独立线程中运行 Mitmproxy 事件循环
        """
        asyncio.set_event_loop(self.loop)
        opts = options.Options(listen_host=self.host, listen_port=self.port)
        
        try:
            # 在事件循环运行中创建 DumpMaster
            async def create_and_run():
                self.master = DumpMaster(opts, with_termlog=False, with_dumper=False)
                # 添加自定义插件
                self.master.addons.add(AIInterceptorAddon())
                await self.master.run()
            
            self.loop.run_until_complete(create_and_run())
        except Exception as e:
            print(f"Mitmproxy error: {e}")
        finally:
            self.loop.close()

    def stop(self):
        """停止 Mitmproxy 代理服务"""
        if self.master:
            self.master.shutdown()
        self._started = False

    @property
    def proxy_url(self) -> str:
        """
        获取代理 URL
        
        Returns:
            代理地址，如 http://127.0.0.1:8080
        """
        return f"http://{self.host}:{self.port}"
