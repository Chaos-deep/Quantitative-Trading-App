"""股票查询端点：/stocks/search 与 /stocks/{code}/bars。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import DailyBar, Stock
from app.schemas.schemas import BarOut, StockOut

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/search", response_model=list[StockOut])
def search_stocks(q: str, limit: int = 20, db: Session = Depends(get_db)):
    """模糊搜索股票代码/名称（用于持仓录入时的股票存在性校验）。"""
    if not q:
        return []
    limit = max(1, min(limit, 50))
    pattern = f"%{q}%"
    rows = db.scalars(
        select(Stock)
        .where(Stock.code.ilike(pattern) | Stock.name.ilike(pattern))
        .order_by(Stock.code.asc())
        .limit(limit)
    ).all()
    return rows


@router.get("/{code}/bars", response_model=list[BarOut])
def get_stock_bars(code: str, limit: int = 120, db: Session = Depends(get_db)):
    """个股日线（二期详情页使用，本期预留）。"""
    stock = db.get(Stock, code)
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="股票不存在")
    limit = max(1, min(limit, 500))
    bars = db.scalars(
        select(DailyBar)
        .where(DailyBar.stock_code == code)
        .order_by(DailyBar.date.asc())
        .limit(limit)
    ).all()
    return bars
