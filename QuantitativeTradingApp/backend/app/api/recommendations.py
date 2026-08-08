"""推荐端点：/recommendations/global 与 /recommendations/personal。"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi.errors import RateLimitExceeded
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import _user_rate_key, get_current_user, limiter
from app.models import Recommendation, Stock, User, UserPersonalAdvice
from app.schemas.schemas import Page, PersonalAdviceOut, RecommendationOut

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _latest_run_date(db: Session) -> date | None:
    return db.scalar(select(func.max(Recommendation.run_date)))


@router.get("/global", response_model=Page[RecommendationOut])
@limiter.limit("60/minute", key_func=_user_rate_key)
def get_global(
    request: Request,
    strategy: Optional[str] = None,
    date_: Optional[date] = None,
    signal: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "score",
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    run_date = date_ or _latest_run_date(db)
    if run_date is None:
        return Page(items=[], total=0, page=1, limit=limit)

    filters = [Recommendation.run_date == run_date]
    if strategy:
        filters.append(Recommendation.strategy == strategy)
    if signal:
        filters.append(Recommendation.signal == signal)

    total = db.scalar(select(func.count()).select_from(Recommendation).where(*filters)) or 0

    order = (
        Recommendation.score.asc()
        if order_by == "score_asc"
        else Recommendation.score.desc()
    )
    rows = (
        db.execute(
            select(Recommendation, Stock.name)
            .join(Stock, Stock.code == Recommendation.stock_code)
            .where(*filters)
            .order_by(order, Recommendation.id.asc())
            .offset(offset)
            .limit(limit)
        )
        .all()
    )
    items = [
        RecommendationOut(
            stock_code=rec.stock_code,
            stock_name=name,
            strategy=rec.strategy,
            run_date=rec.run_date,
            signal=rec.signal,
            score=float(rec.score),
            close=rec.close,
            reason=rec.reason,
        )
        for rec, name in rows
    ]
    return Page(items=items, total=total, page=offset // limit + 1, limit=limit)


@router.get("/personal", response_model=Page[PersonalAdviceOut])
@limiter.limit("60/minute", key_func=_user_rate_key)
def get_personal(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    advice_date = db.scalar(
        select(func.max(UserPersonalAdvice.advice_date)).where(
            UserPersonalAdvice.user_id == current.id
        )
    )
    if advice_date is None:
        return Page(items=[], total=0, page=1, limit=limit)

    filters = [
        UserPersonalAdvice.user_id == current.id,
        UserPersonalAdvice.advice_date == advice_date,
    ]
    total = (
        db.scalar(select(func.count()).select_from(UserPersonalAdvice).where(*filters))
        or 0
    )
    # 排序 SQL（docs/appendices/api/recommendations/personal.md）：
    # ORDER BY CASE WHEN action='BUY' THEN 0 WHEN action='SELL' THEN 1 ELSE 2 END, id DESC
    order = case(
        (UserPersonalAdvice.action == "BUY", 0),
        (UserPersonalAdvice.action == "SELL", 1),
        else_=2,
    )
    rows = (
        db.execute(
            select(UserPersonalAdvice, Stock.name)
            .join(Stock, Stock.code == UserPersonalAdvice.stock_code)
            .where(*filters)
            .order_by(order, UserPersonalAdvice.id.desc())
            .offset(offset)
            .limit(limit)
        )
        .all()
    )
    items = [
        PersonalAdviceOut(
            stock_code=a.stock_code,
            stock_name=name,
            advice_date=a.advice_date,
            action=a.action,
            suggested_shares=a.suggested_shares,
            reason=a.reason,
            strategy_signals=a.strategy_signals,
        )
        for a, name in rows
    ]
    return Page(items=items, total=total, page=offset // limit + 1, limit=limit)
