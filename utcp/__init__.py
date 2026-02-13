# -*- coding: utf-8 -*-
"""
UTCP 协议接口包：按功能拆分为独立模块，各模块在 blueprint 上注册路由。
- blueprint: 统一 Blueprint
- health: 健康检查
- datetime_tool: 日期时间工具
"""
from .blueprint import utcp_bp

# 导入以完成路由注册（各模块内 @utcp_bp.route(...)）
from . import health  # noqa: F401
from . import datetime_tool  # noqa: F401

__all__ = ["utcp_bp"]
