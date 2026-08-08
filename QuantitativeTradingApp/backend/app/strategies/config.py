"""策略参数外置（全部集中在 config，便于调参，不散落在策略代码中）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TurtleParams:
    """海龟策略（A 股收盘价突破改造）。

    docs/design.md §5.2 策略一 + docs/appendices/turtle/ 参考。
    """

    # 唐奇安通道：入场周期（System1/System2）、离场周期
    entry_periods: tuple[int, int] = (20, 55)
    exit_periods: tuple[int, int] = (10, 20)
    atr_period: int = 20
    # 过滤：上市不足 60 日（需至少 60 根 K 线）、低波动、无量
    min_bars: int = 60
    min_atr_ratio: float = 0.005  # ATR(20) / 收盘价 低于此值视为低波动，跳过
    min_avg_volume: float = 1000.0  # 近 60 日均量（手）低于此值视为无量，跳过
    # 评分权重
    score_base: float = 30.0
    score_breakout_weight: float = 200.0
    score_slope_weight: float = 500.0
    score_volume_weight: float = 15.0


@dataclass(frozen=True)
class BollingerParams:
    """布林带均值回归策略。

    docs/design.md §5.2 策略二。
    """

    period: int = 20
    num_std: float = 2.0
    rsi_period: int = 14
    oversold: float = 30.0  # RSI < 30 入场
    exit_rsi: float = 50.0  # RSI > 50 反弹回中轨
    year_line: int = 250  # 年线 MA(250)
    trend_filter_ratio: float = 0.8  # 收盘价 < 年线 × 0.8 视为趋势性下跌，跳过
    min_bars: int = 21  # 至少 20 日窗口 + 1
    score_band_weight: float = 300.0
    score_rsi_weight: float = 1.2
