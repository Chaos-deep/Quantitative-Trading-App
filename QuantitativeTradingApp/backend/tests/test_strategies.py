"""策略单元测试：海龟趋势跟踪 + 布林带均值回归。"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.strategies.bollinger_reversion import BollingerMeanReversionStrategy
from app.strategies.turtle import TurtleStrategy

BUY = "BUY"
HOLD = "HOLD"


def _df(closes: list[float], volume: int = 10000) -> pd.DataFrame:
    today = date(2026, 7, 31)
    dates = [
        (today - timedelta(days=len(closes) - 1 - i)).isoformat()
        for i in range(len(closes))
    ]
    df = pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [volume] * len(closes),
        }
    )
    df.attrs["stock_code"] = "600000.SH"
    return df


def test_turtle_buy_signal():
    closes = [10.0 + 0.05 * (i % 4) for i in range(60)] + [10.5, 10.8, 11.2, 11.6, 12.0]
    rec = TurtleStrategy().run(_df(closes))
    assert rec is not None
    assert rec.signal == BUY
    assert 0 <= rec.score <= 100


def test_turtle_hold_when_no_breakout():
    closes = [10.0 + 0.05 * (i % 4) for i in range(70)]
    rec = TurtleStrategy().run(_df(closes))
    assert rec is not None
    assert rec.signal == HOLD


def test_turtle_insufficient_data_returns_none():
    assert TurtleStrategy().run(_df([10.0] * 30)) is None


def test_bollinger_buy_on_oversold():
    closes = [10.0] * 20 + [8.0]
    rec = BollingerMeanReversionStrategy().run(_df(closes))
    assert rec is not None
    assert rec.signal == BUY
    assert 0 <= rec.score <= 100


def test_bollinger_hold_at_mean():
    closes = [10.0] * 30
    rec = BollingerMeanReversionStrategy().run(_df(closes))
    assert rec is not None
    assert rec.signal == HOLD


def test_bollinger_insufficient_data_returns_none():
    assert BollingerMeanReversionStrategy().run(_df([10.0] * 10)) is None
