"""种子脚本：开发/演示用数据（幂等，可重复执行）。

docs/appendices/deployment/seed.md：
- 示例用户：admin / alice / bob，含持仓与偏好，便于验证模块三个性化建议
- 口令不写入代码：从环境变量 SEED_<USERNAME>_PASSWORD 读取；
  未设置时随机生成并仅打印一次，请立即保存
- 仅用于开发与演示环境
"""

from __future__ import annotations

import os
import secrets
import string
import sys

from sqlalchemy import select

from app.core import database
from app.core.security import hash_password
from app.models import Stock, User, UserPosition, UserPreference
from app.utils.db import upsert_rows

# 示例用户（不含任何口令；口令运行时从环境变量读取或随机生成）
SEED_USERS = [
    {
        "username": "admin",
        "risk_level": "aggressive",
        "total_capital": "1000000",
        "positions": [("600000.SH", 2000)],
    },
    {
        "username": "alice",
        "risk_level": "moderate",
        "total_capital": "500000",
        "positions": [("000001.SZ", 1000), ("600036.SH", 500)],
    },
    {
        "username": "bob",
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


def _password_env_key(username: str) -> str:
    return f"SEED_{username.upper()}_PASSWORD"


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
                env_key = _password_env_key(cfg["username"])
                password = os.getenv(env_key)
                generated = not password
                if generated:
                    password = _generate_password()
                user = User(
                    username=cfg["username"],
                    password_hash=hash_password(password),
                )
                db.add(user)
                db.flush()
                if generated:
                    print(
                        f"创建用户: {cfg['username']}  随机口令: {password}"
                        f"  （仅显示一次，请立即保存）"
                    )
                else:
                    print(f"创建用户: {cfg['username']}  口令来源: 环境变量 {env_key}")
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
        print(
            "提示：口令来自 SEED_<用户名>_PASSWORD 环境变量；"
            "未设置时为随机生成并仅打印一次。"
        )
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(seed())
