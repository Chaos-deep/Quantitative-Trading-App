# 附录 · 数据库 · DDL（建表语句）

> 主文档：../../design.md · 版本随 v0.4 同步

以下为 PostgreSQL 建表语句，命名全部采用 `snake_case`，索引按「`idx_` + 用途」命名。

```sql
-- users
CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,           -- bcrypt
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- stocks
CREATE TABLE stocks (
    code       VARCHAR(16) PRIMARY KEY,            -- 如 600000.SH / 000001.SZ
    name       VARCHAR(64) NOT NULL,
    market     VARCHAR(16),                        -- SH/SZ/BJ，预留 HK/US
    status     VARCHAR(16) DEFAULT 'active',       -- active/suspended/delisted
    updated_at TIMESTAMPTZ                          -- 最后行情时间
);

-- daily_bars
CREATE TABLE daily_bars (
    stock_code VARCHAR(16)   NOT NULL REFERENCES stocks(code),
    date       DATE         NOT NULL,
    open       NUMERIC(12,4) NOT NULL,
    high       NUMERIC(12,4) NOT NULL,
    low        NUMERIC(12,4) NOT NULL,
    close      NUMERIC(12,4) NOT NULL,
    volume     NUMERIC(20,0) NOT NULL,             -- 单位：手
    amount     NUMERIC(20,2),
    PRIMARY KEY (stock_code, date)
);

-- strategy_runs
CREATE TABLE strategy_runs (
    id          BIGSERIAL PRIMARY KEY,             -- run_id
    strategy    VARCHAR(32) NOT NULL,              -- turtle / bollinger_mean_reversion
    run_date    DATE NOT NULL,
    status      VARCHAR(16) DEFAULT 'pending',     -- pending/running/success/failed
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    stock_count INT,
    note        TEXT                               -- 失败清单 / 错误信息
);
CREATE INDEX idx_strategy_runs ON strategy_runs (strategy, run_date);

-- recommendations
CREATE TABLE recommendations (
    id         BIGSERIAL PRIMARY KEY,
    run_id     BIGINT NOT NULL REFERENCES strategy_runs(id),
    run_date   DATE NOT NULL,
    strategy   VARCHAR(32) NOT NULL,
    stock_code VARCHAR(16) NOT NULL REFERENCES stocks(code),
    signal     VARCHAR(8) NOT NULL,                -- BUY/HOLD/AVOID
    score      NUMERIC(6,2) NOT NULL,              -- 0-100
    close      NUMERIC(12,4) NOT NULL,             -- 当日收盘价，供模块三计算建议股数
    reason     TEXT,
    UNIQUE (strategy, run_date, stock_code)
);
CREATE INDEX idx_rec_query ON recommendations (strategy, run_date, score DESC);
CREATE INDEX idx_rec_stock ON recommendations (stock_code, run_date);

-- user_positions
CREATE TABLE user_positions (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    stock_code VARCHAR(16) NOT NULL REFERENCES stocks(code),
    shares     INT NOT NULL,                       -- 持有股数（单位：股）
    cost_price NUMERIC(12,4),
    buy_date   DATE,
    UNIQUE (user_id, stock_code)
);

-- user_preferences
CREATE TABLE user_preferences (
    user_id      BIGINT PRIMARY KEY REFERENCES users(id),  -- 一用户一行
    risk_level   VARCHAR(16) DEFAULT 'moderate',   -- aggressive/moderate/conservative
    total_capital NUMERIC(16,2),                   -- 总资金量（元），NULL 视为未配置
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- user_personal_advice
CREATE TABLE user_personal_advice (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id),
    stock_code       VARCHAR(16) NOT NULL REFERENCES stocks(code),
    advice_date      DATE NOT NULL,
    action           VARCHAR(8) NOT NULL,          -- BUY/SELL/HOLD
    suggested_shares INT NOT NULL,                 -- BUY=加仓/买入量，SELL=清仓量，HOLD=0
    reason           TEXT,
    UNIQUE (user_id, stock_code, advice_date)
);
CREATE INDEX idx_advice_user_date_action ON user_personal_advice (user_id, advice_date, action);
```

> 建表语句中 `strategy_runs` / `recommendations` / `user_personal_advice` 的辅助索引以独立 `CREATE INDEX` 语句建立。

## 索引设计要点

- `idx_rec_query (strategy, run_date, score DESC)`：全局推荐默认查询路径 `WHERE strategy=? AND run_date=? ORDER BY score DESC LIMIT ?` 完全命中，避免 filesort。
- `idx_rec_stock (stock_code, run_date)`：模块三以当日 `recommendations` 为主体 join 持仓/偏好时使用，也支持个股推荐回溯。
- `idx_advice_user_date_action (user_id, advice_date, action)`：个性化列表按 `CASE WHEN action='BUY' THEN 0 ...` 排序，B-tree 支持 `(user_id, advice_date)` 前缀扫描。
- `daily_bars` 复合主键 `(stock_code, date)` 已覆盖个股行情查询，无需额外索引。

## 迁移管理

数据库结构变更统一通过 Alembic 管理（`docker compose run backend alembic upgrade head`），禁止手写变更 SQL 到生产环境。

[← 返回 design.md](../../design.md)
