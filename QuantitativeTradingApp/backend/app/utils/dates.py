"""时区与日期工具。所有定时任务、日期存储统一 Asia/Shanghai。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def now_shanghai() -> datetime:
    """返回当前 Asia/Shanghai 时区的 aware datetime。"""
    return datetime.now(SHANGHAI_TZ)


def today_shanghai() -> date:
    """返回当前 Asia/Shanghai 时区的日期。"""
    return now_shanghai().date()


def to_shanghai(dt: datetime) -> datetime:
    """将任意 datetime 归一化到 Asia/Shanghai 时区（naive 视为上海时区）。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=SHANGHAI_TZ)
    return dt.astimezone(SHANGHAI_TZ)


def to_utc(dt: datetime) -> datetime:
    """转换为 UTC（用于 TIMESTAMPTZ 存储，Postgres 自动处理）。"""
    return to_shanghai(dt).astimezone(ZoneInfo("UTC"))


def trading_window(day: date) -> tuple[datetime, datetime]:
    """交易日当天 00:00:00 - 23:59:59（上海时区）。"""
    start = datetime.combine(day, time.min, tzinfo=SHANGHAI_TZ)
    end = datetime.combine(day, time.max, tzinfo=SHANGHAI_TZ)
    return start, end
