"""布林带均值回归策略。

docs/design.md §5.2 策略二；参数见 config.BollingerParams。
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from app.strategies.base import AVOID, BUY, HOLD, BaseStrategy, Recommendation
from app.strategies.config import BollingerParams
from app.strategies.turtle import _to_date, _last_volume_ratio


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder 平滑 RSI。"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return rsi.fillna(50.0)


class BollingerMeanReversionStrategy(BaseStrategy):
    name = "bollinger_mean_reversion"
    display_name = "布林"
    description = "布林带均值回归（触及下轨 + RSI 超卖反弹）"

    def __init__(self, params: BollingerParams | None = None):
        self.p = params or BollingerParams()

    def run(self, bars: pd.DataFrame) -> Recommendation | None:
        if bars is None or len(bars) < self.p.min_bars:
            return None

        close = bars["close"].astype(float)
        close_now = float(close.iloc[-1])

        mid = close.rolling(self.p.period).mean()
        std = close.rolling(self.p.period).std()
        upper = mid + self.p.num_std * std
        lower = mid - self.p.num_std * std
        mid_now = float(mid.iloc[-1])
        lower_now = float(lower.iloc[-1])

        rsi = calc_rsi(close, self.p.rsi_period)
        rsi_now = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2]) if len(rsi) >= 2 else rsi_now
        close_prev = float(close.iloc[-2]) if len(close) >= 2 else close_now
        vol_ratio = _last_volume_ratio(bars)

        # 趋势性下跌过滤：收盘价低于年线 20% 以上（需足够年线窗口）
        if len(bars) >= self.p.year_line:
            ma250 = float(close.rolling(self.p.year_line).mean().iloc[-1])
            if ma250 > 0 and close_now < ma250 * self.p.trend_filter_ratio:
                return None

        signal: str
        score: float
        reason: str
        if close_now <= lower_now and rsi_now < self.p.oversold:
            signal = BUY
            deviation = max(0.0, lower_now / close_now - 1.0) if close_now > 0 else 0.0
            s = 40.0
            s += min(40.0, deviation * self.p.score_band_weight)
            s += min(20.0, max(0.0, (self.p.oversold - rsi_now) * self.p.score_rsi_weight))
            if vol_ratio < 0.9:
                s += 10.0  # 缩量止跌加分
            score = round(float(np.clip(s, 0, 100)), 2)
            reason = (
                f"收盘价{close_now:.2f}触及布林带下轨{lower_now:.2f}"
                f"，RSI={rsi_now:.0f}超卖，存在均值回归机会"
            )
        elif close_now >= mid_now or rsi_now > self.p.exit_rsi:
            signal = HOLD
            s = 50.0 + min(15.0, max(0.0, (close_now / mid_now - 1.0) * 100.0)) if mid_now > 0 else 50.0
            score = round(float(np.clip(s, 0, 100)), 2)
            reason = "价格反弹回中轨，布林带内震荡企稳"
        elif close_now < lower_now and rsi_now < rsi_prev and close_now < close_prev:
            signal = AVOID
            depth = max(0.0, lower_now / close_now - 1.0) if close_now > 0 else 0.0
            s = 15.0 + min(20.0, depth * self.p.score_band_weight)
            score = round(float(np.clip(s, 0, 100)), 2)
            reason = "跌破布林带下轨且 RSI 走弱，价格转弱"
        else:
            signal = HOLD
            score = 50.0
            reason = "布林带内运行，暂无明确信号"

        return Recommendation(
            strategy=self.name,
            run_date=_to_date(bars["date"].iloc[-1]),
            stock_code=bars.attrs.get("stock_code", ""),
            signal=signal,
            score=score,
            close=close_now,
            reason=reason,
        )
