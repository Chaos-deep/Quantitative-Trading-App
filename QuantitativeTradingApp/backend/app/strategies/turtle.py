"""海龟趋势跟踪策略（A 股改造：收盘价突破）。

docs/design.md §5.2 策略一；参数见 config.TurtleParams。
"""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.strategies.base import AVOID, BUY, HOLD, BaseStrategy, Recommendation
from app.strategies.config import TurtleParams


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """真实波幅周期均值（docs/appendices/turtle/code.md）。"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _to_date(value) -> _date:
    if isinstance(value, _date) and not isinstance(value, datetime):
        return value
    if hasattr(value, "date"):
        return value.date()
    return _date.fromisoformat(str(value)[:10])


def _last_volume_ratio(bars: pd.DataFrame) -> float:
    """最新成交量 / 5 日均量。"""
    vol = bars["volume"].astype(float)
    last = float(vol.iloc[-1])
    avg5 = float(vol.tail(6).iloc[:-1].mean())
    return last / avg5 if avg5 > 0 else 1.0


class TurtleStrategy(BaseStrategy):
    name = "turtle"
    display_name = "海龟"
    description = "海龟趋势跟踪（收盘价突破唐奇安通道，20/55 日双系统）"

    def __init__(self, params: TurtleParams | None = None):
        self.p = params or TurtleParams()

    # ---- 过滤 ----

    def _filter(self, bars: pd.DataFrame, atr: float, close_now: float) -> Optional[str]:
        if len(bars) < self.p.min_bars:
            return f"上市不足 {self.p.min_bars} 日"
        if np.isnan(atr) or atr <= 0 or close_now <= 0:
            return "波动率数据不足"
        # 低波动：ATR 相对价格过小
        if atr / close_now < self.p.min_atr_ratio:
            return "低波动标的"
        # 无量：近 60 日均量不足
        avg_vol = float(bars["volume"].tail(60).astype(float).mean())
        if avg_vol < self.p.min_avg_volume:
            return "流动性不足"
        return None

    # ---- 评分 ----

    def _score_buy(self, close: float, entry_channel: float, ma20: float, ma20_prev: float, vol_ratio: float) -> float:
        breakout_strength = max(0.0, close / entry_channel - 1.0) if entry_channel > 0 else 0.0
        trend_slope = (ma20 - ma20_prev) / ma20_prev if ma20_prev else 0.0
        s = self.p.score_base
        s += min(35.0, breakout_strength * self.p.score_breakout_weight)
        s += min(20.0, max(0.0, trend_slope * self.p.score_slope_weight))
        s += min(15.0, max(0.0, (vol_ratio - 1.0) * self.p.score_volume_weight))
        return round(float(np.clip(s, 0, 100)), 2)

    def _score_avoid(self, close: float, exit_channel: float) -> float:
        depth = max(0.0, exit_channel / close - 1.0) if close > 0 else 0.0
        s = 20.0 + min(20.0, depth * self.p.score_breakout_weight)
        return round(float(np.clip(s, 0, 100)), 2)

    def _score_hold(self, close: float, ma20: float) -> float:
        s = 45.0
        if ma20 and close > ma20:
            s += min(15.0, (close / ma20 - 1.0) * 100.0)
        return round(float(np.clip(s, 0, 100)), 2)

    # ---- 主入口 ----

    def run(self, bars: pd.DataFrame) -> Recommendation | None:
        if bars is None or len(bars) < self.p.min_bars:
            return None
        high = bars["high"].astype(float)
        low = bars["low"].astype(float)
        close = bars["close"].astype(float)
        close_now = float(close.iloc[-1])

        atr = float(calc_atr(high, low, close, self.p.atr_period).iloc[-1])
        reason_filter = self._filter(bars, atr, close_now)
        if reason_filter:
            return None

        # 唐奇安通道（排除今日，避免收盘价与自身比较）
        entry_20 = float(high.iloc[-21:-1].max())
        entry_55 = float(high.iloc[-56:-1].max())
        exit_10 = float(low.iloc[-11:-1].min())
        exit_20 = float(low.iloc[-21:-1].min())

        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma20_prev = float(close.rolling(20).mean().iloc[-11])
        vol_ratio = _last_volume_ratio(bars)

        signal: str
        score: float
        reason: str
        if close_now > entry_20 or close_now > entry_55:
            if close_now > entry_20:
                channel, period = entry_20, 20
            else:
                channel, period = entry_55, 55
            signal = BUY
            score = self._score_buy(close_now, channel, ma20, ma20_prev, vol_ratio)
            reason = (
                f"收盘价{close_now:.2f}突破{period}日高点{channel:.2f}"
                f"，量能放大{vol_ratio:.1f}倍"
            )
            if ma20 and close_now > ma20:
                reason += "，20日均线上行"
        elif close_now < exit_10 or close_now < exit_20:
            channel = min(exit_10, exit_20)
            signal = AVOID
            score = self._score_avoid(close_now, channel)
            reason = f"收盘价{close_now:.2f}跌破离场通道{channel:.2f}，趋势破位"
        else:
            signal = HOLD
            score = self._score_hold(close_now, ma20)
            reason = "收盘价未突破入场通道，趋势仍在延续"

        return Recommendation(
            strategy=self.name,
            run_date=_to_date(bars["date"].iloc[-1]),
            stock_code=bars.attrs.get("stock_code", ""),
            signal=signal,
            score=score,
            close=close_now,
            reason=reason,
        )
