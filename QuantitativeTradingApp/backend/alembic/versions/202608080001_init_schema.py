"""init schema (v0.5)

Revision ID: 202608080001
Revises:
Create Date: 2026-08-08 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "202608080001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.BIGSERIAL(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "stocks",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("market", sa.String(16)),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "daily_bars",
        sa.Column("stock_code", sa.String(16), sa.ForeignKey("stocks.code"), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.Numeric(20, 0), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2)),
    )

    op.create_table(
        "strategy_runs",
        sa.Column("id", postgresql.BIGSERIAL(), primary_key=True),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("stock_count", sa.Integer()),
        sa.Column("note", sa.Text()),
    )
    op.create_index("idx_strategy_runs", "strategy_runs", ["strategy", "run_date"])

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.BIGSERIAL(), primary_key=True),
        sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("strategy_runs.id"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("stock_code", sa.String(16), sa.ForeignKey("stocks.code"), nullable=False),
        sa.Column("signal", sa.String(8), nullable=False),
        sa.Column("score", sa.Numeric(6, 2), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.UniqueConstraint("strategy", "run_date", "stock_code", name="uq_recommendations_strategy_run_date_stock"),
    )
    op.create_index("idx_rec_query", "recommendations", ["strategy", "run_date", sa.text("score DESC")])
    op.create_index("idx_rec_stock", "recommendations", ["stock_code", "run_date"])

    op.create_table(
        "user_positions",
        sa.Column("id", postgresql.BIGSERIAL(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stock_code", sa.String(16), sa.ForeignKey("stocks.code"), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 4)),
        sa.Column("buy_date", sa.Date()),
        sa.UniqueConstraint("user_id", "stock_code", name="uq_user_positions_user_stock"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("risk_level", sa.String(16), nullable=False, server_default="moderate"),
        sa.Column("total_capital", sa.Numeric(16, 2)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "user_personal_advice",
        sa.Column("id", postgresql.BIGSERIAL(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stock_code", sa.String(16), sa.ForeignKey("stocks.code"), nullable=False),
        sa.Column("advice_date", sa.Date(), nullable=False),
        sa.Column("action", sa.String(8), nullable=False),
        sa.Column("suggested_shares", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("strategy_signals", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.UniqueConstraint("user_id", "stock_code", "advice_date", name="uq_user_personal_advice_user_stock_date"),
    )
    op.create_index(
        "idx_advice_user_date_action",
        "user_personal_advice",
        ["user_id", "advice_date", "action"],
    )


def downgrade() -> None:
    op.drop_index("idx_advice_user_date_action", table_name="user_personal_advice")
    op.drop_table("user_personal_advice")
    op.drop_table("user_preferences")
    op.drop_table("user_positions")
    op.drop_index("idx_rec_stock", table_name="recommendations")
    op.drop_index("idx_rec_query", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("idx_strategy_runs", table_name="strategy_runs")
    op.drop_table("strategy_runs")
    op.drop_table("daily_bars")
    op.drop_table("stocks")
    op.drop_table("users")
