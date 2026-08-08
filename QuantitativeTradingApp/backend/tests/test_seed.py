"""种子脚本幂等性测试：重复执行不产生重复用户。"""

from __future__ import annotations

import os
import types

import pytest
from sqlalchemy import func, select

os.environ.setdefault("APP_ENV", "test")


def test_seed_is_idempotent(monkeypatch, tmp_path):
    db_path = tmp_path / "seed.db"

    from app.core import database
    from app.models import Base, User

    # get_settings() 是 lru_cache，直接 monkeypatch 数据库模块内的引用，
    # 避免污染全局缓存的 Settings 对象
    fake_settings = types.SimpleNamespace(database_url=f"sqlite:///{db_path}")
    monkeypatch.setattr(database, "get_settings", lambda: fake_settings)

    database.init_engine()
    Base.metadata.create_all(database.engine)

    from seed import seed

    seed()
    seed()

    with database.engine.connect() as conn:
        count = conn.execute(select(func.count()).select_from(User)).scalar()
    assert count == 3
