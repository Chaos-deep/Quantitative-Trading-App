"""流水线入口：run_pipeline_core（纯业务计算，不涉及 strategy_runs 状态更新）。

步骤（docs/appendices/pipeline/overview.md 3-7）：
3. 模块一：同步股票列表（增量 upsert）
4. 模块一：拉取全市场日线（批量写入 daily_bars）
5/6. 模块二：逐股流式运行双策略 → recommendations
7. 模块三：批量加载 → 聚合 → upsert user_personal_advice
状态更新（步骤 0/1/2/8/9）由调度层负责（scheduler.py）。
"""

from __future__ import annotations

import time
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.market_data import MarketDataService, TradingCalendar
from app.services.personal_advisor import run_personal_advisor
from app.services.strategy_engine import run_strategies
from app.utils.logging import get_logger

logger = get_logger("pipeline")


def run_pipeline_core(
    run_date: date,
    run_ids: dict[str, int],
    session: Optional[Session] = None,
) -> dict:
    """执行流水线纯计算部分（步骤 3-7），返回汇总指标。

    参数 run_ids 由调度层预创建（strategy 名 → run_id），用于写 recommendations。
    本函数不创建/更新 strategy_runs 状态。
    """
    own_session = session is None
    if own_session:
        session = SessionLocal()
    start = time.monotonic()
    try:
        market = MarketDataService(session)
        calendar = TradingCalendar()

        # 步骤 3：股票列表增量同步
        stock_stats = market.sync_stock_list()

        # 步骤 4：全市场日线
        bar_stats = market.fetch_all_daily_bars(run_date)

        # 步骤 5/6：双策略
        strategy_results = run_strategies(session, run_date, run_ids)

        # 步骤 7：模块三
        advice_count = run_personal_advisor(session, run_date)

        strategy_counts = {r.strategy: r.produced for r in strategy_results}
        duration = round(time.monotonic() - start, 2)
        note_parts: list[str] = []
        if bar_stats.failed:
            note_parts.append(f"拉取失败{len(bar_stats.failed)}只：{','.join(bar_stats.failed[:50])}")
        if bar_stats.degraded:
            note_parts.append(f"降级备用源{len(bar_stats.degraded)}只")
        strategy_errors = sum(len(r.errors) for r in strategy_results)
        if strategy_errors:
            note_parts.append(f"策略异常{strategy_errors}只")

        summary = {
            "run_date": run_date.isoformat(),
            "stock_count": bar_stats.total,
            "ok_stock_count": bar_stats.ok,
            "failed_stock_count": len(bar_stats.failed),
            "degraded_stock_count": len(bar_stats.degraded),
            "strategy_counts": strategy_counts,
            "advice_count": advice_count,
            "duration_seconds": duration,
            "note": "；".join(note_parts) or "成功",
        }
        logger.info("流水线核心执行完成", **summary)
        return summary
    finally:
        if own_session:
            session.close()
