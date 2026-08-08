"""模块二·策略引擎：逐股流式运行注册策略，写 recommendations。

内存约束（§6）：严禁一次性加载全表 daily_bars；按股票循环，单次仅查该股
最近 500 条 K 线，计算完立即释放 DataFrame，内存峰值 ≤200MB。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyBar, Recommendation, Stock
from app.strategies import STRATEGY_REGISTRY, BaseStrategy
from app.strategies.base import Recommendation as StrategyRec
from app.utils.db import upsert_rows
from app.utils.logging import get_logger

logger = get_logger("strategy_engine")

MAX_BARS = 500  # 足够覆盖 MA(250)、ATR(60) 等指标窗口


@dataclass
class StrategyRunResult:
    strategy: str
    produced: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def load_stock_bars(session: Session, stock_code: str) -> pd.DataFrame | None:
    """单股最近 500 条 K 线（升序）。"""
    rows = (
        session.execute(
            select(DailyBar)
            .where(DailyBar.stock_code == stock_code)
            .order_by(DailyBar.date.desc())
            .limit(MAX_BARS)
        )
        .scalars()
        .all()
    )
    if not rows:
        return None
    df = pd.DataFrame(
        [
            {
                "date": r.date,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume),
                "amount": float(r.amount) if r.amount is not None else None,
            }
            for r in reversed(rows)  # 还原为升序
        ]
    )
    return df


def is_st(name: str | None) -> bool:
    return bool(name and "ST" in name.upper())


def run_single_strategy(
    session: Session,
    run_date: date,
    run_id: int,
    strategy: BaseStrategy,
) -> StrategyRunResult:
    result = StrategyRunResult(strategy=strategy.name)

    stocks = session.execute(
        select(Stock.code, Stock.name).where(Stock.status == "active")
    ).all()

    to_write: list[dict] = []
    for code, name in stocks:
        if is_st(name):
            result.skipped += 1
            continue
        df = load_stock_bars(session, code)
        if df is None:
            result.skipped += 1
            continue
        try:
            df.attrs["stock_code"] = code
            rec = strategy.run(df)
            if rec is not None:
                to_write.append(
                    {
                        "run_id": run_id,
                        "run_date": run_date,
                        "strategy": strategy.name,
                        "stock_code": code,
                        "signal": rec.signal,
                        "score": round(rec.score, 2),
                        "close": rec.close,
                        "reason": rec.reason,
                    }
                )
        except Exception as e:  # noqa: BLE001  单股异常不影响其余股票
            logger.error("策略[%s] 计算异常 %s: %s", strategy.name, code, e, exc_info=True)
            result.errors.append(f"{code}: {e}")
        finally:
            del df  # 立即释放单股 DataFrame，控制内存峰值

    upsert_rows(
        session,
        Recommendation,
        to_write,
        index_elements=["strategy", "run_date", "stock_code"],
        update_columns=["run_id", "signal", "score", "close", "reason"],
    )
    result.produced = len(to_write)
    return result


def run_strategies(
    session: Session,
    run_date: date,
    run_ids: dict[str, int],
    strategies: Sequence[BaseStrategy] | None = None,
) -> list[StrategyRunResult]:
    """依次运行全部注册策略，返回各策略结果。"""
    if strategies is None:
        strategies = [cls() for cls in STRATEGY_REGISTRY.values()]
    results = []
    for strategy in strategies:
        run_id = run_ids[strategy.name]
        result = run_single_strategy(session, run_date, run_id, strategy)
        results.append(result)
        logger.info(
            "策略完成",
            strategy=strategy.name,
            produced=result.produced,
            skipped=result.skipped,
            errors=len(result.errors),
        )
    session.commit()
    return results
