"""用户数据端点：positions / preferences / strategies / health。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Stock, User, UserPosition, UserPreference
from app.schemas.schemas import (
    PositionIn,
    PositionOut,
    PreferencesIn,
    PreferencesOut,
    StrategyMeta,
)
from app.strategies.base import all_strategy_meta
from app.utils.db import upsert_rows

router = APIRouter(tags=["user-data"])


# ---------- 持仓 ----------

@router.post("/positions", response_model=PositionOut)
def upsert_position(
    payload: PositionIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    stock = db.get(Stock, payload.stock_code)
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="股票不存在")

    upsert_rows(
        db,
        UserPosition,
        [
            {
                "user_id": current.id,
                "stock_code": payload.stock_code,
                "shares": payload.shares,
                "cost_price": payload.cost_price,
                "buy_date": payload.buy_date,
            }
        ],
        index_elements=["user_id", "stock_code"],
        update_columns=["shares", "cost_price", "buy_date"],
    )
    db.commit()
    row = db.scalar(
        select(UserPosition).where(
            UserPosition.user_id == current.id,
            UserPosition.stock_code == payload.stock_code,
        )
    )
    return row


# ---------- 偏好 ----------

@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    pref = db.get(UserPreference, current.id)
    if pref is None:
        pref = UserPreference(
            user_id=current.id,
            risk_level="moderate",
            total_capital=None,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.put("/preferences", response_model=PreferencesOut)
def put_preferences(
    payload: PreferencesIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    upsert_rows(
        db,
        UserPreference,
        [
            {
                "user_id": current.id,
                "risk_level": payload.risk_level,
                "total_capital": payload.total_capital,
                "updated_at": datetime.now(timezone.utc),
            }
        ],
        index_elements=["user_id"],
        update_columns=["risk_level", "total_capital", "updated_at"],
    )
    db.commit()
    return db.get(UserPreference, current.id)


# ---------- 策略元信息 ----------

@router.get("/strategies", response_model=list[StrategyMeta])
def list_strategies():
    return all_strategy_meta()


# ---------- 健康检查 ----------

@router.get("/health")
def health(db: Session = Depends(get_db)):
    """健康检查（含 DB 连通性），无需认证。"""
    db.execute(select(1))
    return {"status": "ok"}
