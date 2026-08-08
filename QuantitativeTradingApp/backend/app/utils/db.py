"""数据库写入工具：方言感知的 upsert（PostgreSQL 原生 ON CONFLICT，其余回退）。"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.models import Base


def insert_rows_ignore_conflict(
    session: Session,
    model: type[Base],
    rows: Sequence[dict[str, Any]],
    index_elements: Sequence[str],
) -> int:
    """批量插入，冲突时忽略（daily_bars 幂等写入用）。"""
    if not rows:
        return 0
    if session.get_bind().dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(model).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=list(index_elements))
        session.execute(stmt)
        return len(rows)

    # 通用回退：先过滤已存在行再插入
    existing_keys = set()
    for row in rows:
        filters = {k: row[k] for k in index_elements}
        if session.scalar(select(model.id).filter_by(**filters)) is not None:
            existing_keys.add(tuple(row[k] for k in index_elements))
    new_rows = [
        r for r in rows if tuple(r[k] for k in index_elements) not in existing_keys
    ]
    if new_rows:
        session.execute(insert(model).values(new_rows))
    return len(new_rows)


def upsert_rows(
    session: Session,
    model: type[Base],
    rows: Sequence[dict[str, Any]],
    index_elements: Sequence[str],
    update_columns: Sequence[str] | None = None,
) -> int:
    """按 index_elements 做幂等 upsert，返回写入行数。

    - PostgreSQL：`INSERT ... ON CONFLICT DO UPDATE`（原子，无需预查询）。
    - 其他方言（SQLite 测试环境）：逐行查冲突 → update / insert 回退。
    """
    if not rows:
        return 0
    update_columns = update_columns or [c for c in rows[0] if c not in index_elements]
    dialect = session.get_bind().dialect.name

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(model).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=list(index_elements),
            set_={c: stmt.excluded[c] for c in update_columns},
        )
        session.execute(stmt)
        return len(rows)

    # 通用回退（测试 / SQLite）
    count = 0
    for row in rows:
        filters = {k: row[k] for k in index_elements}
        existing = session.scalar(select(model).filter_by(**filters))
        if existing is None:
            session.add(model(**row))
            count += 1
        else:
            for col in update_columns:
                if col in row:
                    setattr(existing, col, row[col])
            count += 1
    session.flush()
    return count
