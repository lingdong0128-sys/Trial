# -*- coding: utf-8 -*-
"""UTCP 工具：获取当前日期、时间及相关数据。"""
from datetime import datetime, timezone, timedelta

from flask import request, jsonify

from .blueprint import utcp_bp


# 默认时区：中国北京时间（UTC+8）
DEFAULT_TIMEZONE_HOURS = 8


def get_datetime(timezone_hours: float = None, **kwargs) -> dict:
    """
    获取当前时间、日期及相关数据。
    参数：
        timezone_hours: 可选，时区偏移（小时），如 8 表示 UTC+8；不传则使用中国北京时间（UTC+8）。
    返回：
        含 success / protocol / message / data 的 dict，data 内含日期时间字段。
    """
    try:
        if timezone_hours is not None:
            tz = timezone(timedelta(hours=float(timezone_hours)))
        else:
            tz = timezone(timedelta(hours=DEFAULT_TIMEZONE_HOURS))
        now = datetime.now(tz)
        offset = now.utcoffset()
        offset_seconds = int(offset.total_seconds()) if offset else 0
        offset_hours = offset_seconds / 3600
        # ISO 8601 时区偏移字符串，如 +08:00、-05:30
        sign = "+" if offset_seconds >= 0 else "-"
        abs_sec = abs(offset_seconds)
        tz_offset_iso = f"{sign}{abs_sec // 3600:02d}:{abs_sec % 3600 // 60:02d}"
        tz_abbr = now.strftime("%Z") or str(tz)
        weekdays_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        wd = now.weekday()
        return {
            "success": True,
            "protocol": "UTCP",
            "message": "ok",
            "data": {
                "iso": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "timestamp": int(now.timestamp()),
                "timestamp_ms": int(now.timestamp() * 1000),
                "timezone": tz_abbr,
                "timezone_offset_hours": offset_hours,
                "timezone_offset": tz_offset_iso,
                "timezone_info": {
                    "name": tz_abbr,
                    "offset_iso": tz_offset_iso,
                    "offset_hours": offset_hours,
                    "utc_equivalent": now.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                },
                "weekday_cn": weekdays_cn[wd],
                "weekday_en": weekdays_en[wd],
                "weekday_num": wd + 1,
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": str(e),
            "data": None,
        }


@utcp_bp.route("/datetime", methods=["GET", "POST"])
def utcp_datetime():
    """UTCP 工具：获取当前日期时间及相关数据"""
    if request.method == "GET":
        tz_hours = request.args.get("timezone_hours")
    else:
        data = request.get_json() or request.form or {}
        data = data if isinstance(data, dict) else {}
        tz_hours = data.get("timezone_hours")
    try:
        tz_hours = float(tz_hours) if tz_hours is not None and str(tz_hours).strip() else None
    except (TypeError, ValueError):
        tz_hours = None
    result = get_datetime(timezone_hours=tz_hours)
    return jsonify(result)
