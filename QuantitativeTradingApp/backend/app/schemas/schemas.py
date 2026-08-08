"""Pydantic API Schema。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------- 通用分页 ----------

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int


# ---------- 认证 ----------

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


# ---------- 推荐 ----------

class RecommendationOut(BaseModel):
    stock_code: str
    stock_name: str | None = None
    strategy: str
    run_date: date
    signal: str
    score: float
    close: Decimal
    reason: str | None = None


class PersonalAdviceOut(BaseModel):
    stock_code: str
    stock_name: str | None = None
    advice_date: date
    action: str
    suggested_shares: int
    close: Decimal | None = None
    reason: str | None = None
    strategy_signals: list[dict] | None = None


# ---------- 股票 ----------

class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    market: str | None = None


class BarOut(BaseModel):
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal | None = None


# ---------- 用户数据 ----------

class PositionIn(BaseModel):
    stock_code: str = Field(min_length=1, max_length=16)
    shares: int = Field(gt=0, description="单位：股（1 手 = 100 股）")
    cost_price: Decimal | None = None
    buy_date: date | None = None


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    stock_code: str
    shares: int
    cost_price: Decimal | None = None
    buy_date: date | None = None


class PreferencesIn(BaseModel):
    risk_level: str = Field(default="moderate", pattern="^(aggressive|moderate|conservative)$")
    total_capital: Decimal | None = Field(default=None, ge=0, description="总资金量（元），NULL 视为未配置")


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    risk_level: str
    total_capital: Decimal | None = None
    updated_at: datetime


# ---------- 策略元信息 ----------

class StrategyMeta(BaseModel):
    name: str
    display_name: str
    description: str
