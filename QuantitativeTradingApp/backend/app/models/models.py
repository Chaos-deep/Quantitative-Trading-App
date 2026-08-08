"""SQLAlchemy 2.0 模型。表结构与 docs/appendices/database/ddl.md 严格一致。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BIGINT,
    NUMERIC,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

# JSONB 在 PostgreSQL 下使用原生 JSONB，SQLite（测试环境）退化为 JSON
JsonB = JSON().with_variant(JSONB, "postgresql")

# PostgreSQL 下为 BIGINT 主键（自动生成 BIGSERIAL）；SQLite（测试环境）退化为 INTEGER PRIMARY KEY 以便自增
BigSerial = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigSerial, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Stock(Base):
    __tablename__ = "stocks"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)  # 如 600000.SH
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str | None] = mapped_column(String(16))  # SH/SZ/BJ，预留 HK/US
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="active"
    )  # active/suspended/delisted
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DailyBar(Base):
    __tablename__ = "daily_bars"
    __table_args__ = (PrimaryKeyConstraint("stock_code", "date"),)

    stock_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("stocks.code"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(NUMERIC(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(NUMERIC(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(NUMERIC(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(NUMERIC(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(NUMERIC(20, 0), nullable=False)  # 单位：手
    amount: Mapped[Decimal | None] = mapped_column(NUMERIC(20, 2))


class StrategyRun(Base):
    __tablename__ = "strategy_runs"
    __table_args__ = (Index("idx_strategy_runs", "strategy", "run_date"),)

    id: Mapped[int] = mapped_column(BigSerial, primary_key=True)  # run_id
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)  # turtle / bollinger_mean_reversion
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="pending"
    )  # pending/running/success/failed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stock_count: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("strategy", "run_date", "stock_code", name="uq_recommendations_strategy_run_date_stock"),
        Index("idx_rec_query", "strategy", "run_date", "score"),
        Index("idx_rec_stock", "stock_code", "run_date"),
    )

    id: Mapped[int] = mapped_column(BigSerial, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("strategy_runs.id"), nullable=False
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    stock_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("stocks.code"), nullable=False
    )
    signal: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY/HOLD/AVOID
    score: Mapped[Decimal] = mapped_column(NUMERIC(6, 2), nullable=False)  # 0-100
    close: Mapped[Decimal] = mapped_column(NUMERIC(12, 4), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


class UserPosition(Base):
    __tablename__ = "user_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "stock_code", name="uq_user_positions_user_stock"),
    )

    id: Mapped[int] = mapped_column(BigSerial, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("users.id"), nullable=False
    )
    stock_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("stocks.code"), nullable=False
    )
    shares: Mapped[int] = mapped_column(Integer, nullable=False)  # 单位：股
    cost_price: Mapped[Decimal | None] = mapped_column(NUMERIC(12, 4))
    buy_date: Mapped[date | None] = mapped_column(Date)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("users.id"), primary_key=True
    )  # 一用户一行
    risk_level: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="moderate"
    )  # aggressive/moderate/conservative
    total_capital: Mapped[Decimal | None] = mapped_column(NUMERIC(16, 2))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserPersonalAdvice(Base):
    __tablename__ = "user_personal_advice"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "stock_code", "advice_date",
            name="uq_user_personal_advice_user_stock_date",
        ),
        Index(
            "idx_advice_user_date_action",
            "user_id", "advice_date", "action",
        ),
    )

    id: Mapped[int] = mapped_column(BigSerial, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("users.id"), nullable=False
    )
    stock_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("stocks.code"), nullable=False
    )
    advice_date: Mapped[date] = mapped_column(Date, nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY/SELL/HOLD
    suggested_shares: Mapped[int] = mapped_column(Integer, nullable=False)  # 单位：股
    reason: Mapped[str | None] = mapped_column(Text)
    strategy_signals: Mapped[list | None] = mapped_column(
        JsonB, nullable=False, server_default="[]"
    )
