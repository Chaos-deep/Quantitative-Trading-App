"""种子脚本：开发/演示用数据（幂等，可重复执行）。

docs/appendices/deployment/seed.md：
- admin 测试用户：admin / admin123
- 2~3 个示例用户：含持仓与偏好，便于验证模块三个性化建议
- 仅用于开发与演示环境
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.core import database
from app.core.security import hash_password
from app.models import Stock, User, UserPosition, UserPreference
from app.utils.db import upsert_rows

# 示例用户（密码明文仅存在于脚本内，生产凭据走环境变量/Secret）
SEED_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "risk_level": "aggressive",
        "total_capital": "1000000",
        "positions": [("600000.SH", 2000)],
    },
    {
        "username": "alice",
        "password": "alice123",
        "risk_level": "moderate",
        "total_capital": "500000",
        "positions": [("000001.SZ", 1000), ("600036.SH", 500)],
    },
    {
        "username": "bob",
        "password": "bob123",
        "risk_level": "conservative",
        "total_capital": "200000",
        "positions": [],
    },
]

# 持仓用示例股票（若不存在则补入，保证 FK 完整）
SEED_STOCKS = [
    ("600000.SH", "浦发银行", "SH"),
    ("000001.SZ", "平安银行", "SZ"),
    ("600036.SH", "招商银行", "SH"),
    ("600519.SH", "贵州茅台", "SH"),
]


def seed() -> None:
    database.init_engine()
    db = database.SessionLocal()
    try:
        # 1. 股票
        upsert_rows(
            db,
            Stock,
            [
                {"code": c, "name": n, "market": m, "status": "active"}
                for c, n, m in SEED_STOCKS
            ],
            index_elements=["code"],
            update_columns=["name", "market", "status"],
        )

        # 2. 用户 / 偏好 / 持仓（幂等：用户名已存在则跳过）
        for cfg in SEED_USERS:
            user = db.scalar(select(User).where(User.username == cfg["username"]))
            if user is None:
                user = User(
                    username=cfg["username"],
                    password_hash=hash_password(cfg["password"]),
                )
                db.add(user)
                db.flush()
                print(f"创建用户: {cfg['username']}")
            else:
                print(f"用户已存在，跳过: {cfg['username']}")

            upsert_rows(
                db,
                UserPreference,
                [
                    {
                        "user_id": user.id,
                        "risk_level": cfg["risk_level"],
                        "total_capital": cfg["total_capital"],
                    }
                ],
                index_elements=["user_id"],
                update_columns=["risk_level", "total_capital"],
            )

            for code, shares in cfg["positions"]:
                stock = db.get(Stock, code)
                if stock is None:
                    continue
                upsert_rows(
                    db,
                    UserPosition,
                    [
                        {
                            "user_id": user.id,
                            "stock_code": code,
                            "shares": shares,
                        }
                    ],
                    index_elements=["user_id", "stock_code"],
                    update_columns=["shares"],
                )
        db.commit()
        print("种子数据写入完成。")
        print("测试账号: admin/admin123, alice/alice123, bob/bob123")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(seed())
