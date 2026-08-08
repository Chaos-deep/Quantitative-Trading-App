"""模块三·用户个性化投顾：内存批量计算 + upsert 写 user_personal_advice。

约束（§5.4/§6）：禁止逐用户重复查库；一次性批量加载当日 recommendations、
全量 user_positions、全量 user_preferences，在内存中完成计算后统一写入。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recommendation, UserPersonalAdvice, UserPosition, UserPreference
from app.strategies.base import AVOID, BUY, HOLD
from app.strategies import STRATEGY_REGISTRY
from app.utils.db import upsert_rows
from app.utils.logging import get_logger

logger = get_logger("personal_advisor")

POSITION_RATIO = 0.05  # 单股仓位：总资金 5%


def calc_suggested_shares(total_capital: Decimal | None, close: float) -> int:
    """`floor(总资金 × 5% / close / 100) × 100`；无资金或不足 1 手返回 0。"""
    if total_capital is None or close <= 0:
        return 0
    budget = float(total_capital) * POSITION_RATIO
    return int(budget / close / 100) * 100


def aggregate_global_signal(strategy_signals: list[dict]) -> str:
    """多策略冲突聚合（§5.4）：AVOID 优先 → BUY → 全 HOLD。"""
    if any(s["signal"] == AVOID for s in strategy_signals):
        return AVOID
    if any(s["signal"] == BUY for s in strategy_signals):
        return BUY
    return HOLD


def _display_name(strategy: str) -> str:
    cls = STRATEGY_REGISTRY.get(strategy)
    return cls.display_name if cls else strategy


def run_personal_advisor(session: Session, run_date: date) -> int:
    """为当日生成全量个性化建议，返回写入行数。"""
    # ---- 一次性批量加载 ----
    recs = session.scalars(
        select(Recommendation).where(Recommendation.run_date == run_date)
    ).all()
    positions = session.scalars(select(UserPosition)).all()
    preferences = session.scalars(select(UserPreference)).all()

    # ---- 按股票聚合（先逐策略记录原始信号，再折叠全局信号）----
    agg: dict[str, dict] = defaultdict(
        lambda: {"signals": [], "scores": [], "reasons": [], "close": 0.0}
    )
    for r in recs:
        a = agg[r.stock_code]
        a["signals"].append({"strategy": r.strategy, "signal": r.signal})
        a["scores"].append(float(r.score))
        a["reasons"].append(f"{_display_name(r.strategy)}：{r.reason or ''}")
        a["close"] = float(r.close)

    stock_advice: dict[str, dict] = {}
    for code, a in agg.items():
        stock_advice[code] = {
            "strategy_signals": a["signals"],
            "global_signal": aggregate_global_signal(a["signals"]),
            "score": round(sum(a["scores"]) / len(a["scores"]), 2) if a["scores"] else 0.0,
            "reason": "；".join(x for x in a["reasons"] if x),
            "close": a["close"],
        }

    # ---- 索引：持仓 / 偏好 ----
    pos_by_user: dict[int, dict[str, int]] = defaultdict(dict)
    for p in positions:
        pos_by_user[p.user_id][p.stock_code] = p.shares
    pref_by_user: dict[int, UserPreference] = {p.user_id: p for p in preferences}

    # ---- 场景映射（§5.4 建议生成规则）----
    rows: list[dict] = []
    user_ids = set(pos_by_user) | set(pref_by_user)
    for user_id in user_ids:
        pref = pref_by_user.get(user_id)
        capital = pref.total_capital if pref else None
        held = pos_by_user.get(user_id, {})
        for code, a in stock_advice.items():
            shares_held = held.get(code)
            action: str
            suggested: int
            reason: str
            if shares_held is not None:
                # 已持仓
                if a["global_signal"] == BUY:
                    action = HOLD
                    suggested = calc_suggested_shares(capital, a["close"])
                    reason = (
                        f"您已持有该股，今日出现买入信号，建议持有并可加仓 {suggested} 股"
                        if suggested > 0
                        else "您已持有该股，今日出现买入信号，建议持有（资金不足 1 手不加仓）"
                    )
                elif a["global_signal"] == HOLD:
                    action = HOLD
                    suggested = 0
                    reason = "您已持有该股，今日信号为持有，建议继续持有"
                else:  # AVOID
                    action = "SELL"
                    suggested = shares_held
                    reason = f"您已持有该股，今日出现卖出信号，建议清仓全部 {shares_held} 股"
            else:
                # 未持仓：仅全局 BUY 且资金足够时生成
                if a["global_signal"] != BUY or capital is None:
                    continue
                suggested = calc_suggested_shares(capital, a["close"])
                if suggested < 100:  # 买不起 1 手则跳过不生成
                    continue
                action = BUY
                reason = f"您未持有该股，今日出现买入信号，建议按资金 5% 仓位买入 {suggested} 股"

            rows.append(
                {
                    "user_id": user_id,
                    "stock_code": code,
                    "advice_date": run_date,
                    "action": action,
                    "suggested_shares": suggested,
                    "reason": reason,
                    "strategy_signals": a["strategy_signals"],
                }
            )

    upsert_rows(
        session,
        UserPersonalAdvice,
        rows,
        index_elements=["user_id", "stock_code", "advice_date"],
        update_columns=["action", "suggested_shares", "reason", "strategy_signals"],
    )
    session.commit()
    logger.info("个性化投顾完成", advice_rows=len(rows), stocks=len(stock_advice), users=len(user_ids))
    return len(rows)
