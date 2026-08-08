# 附录 · 数据库 · recommendations 表

> 主文档：../../../design.md · 版本随 v0.5 同步

## 用途

模块二（策略引擎）产出的全局推荐，双策略共用一张表。

## 表结构

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | |
| run_id | BIGINT | FK→strategy_runs | |
| run_date | DATE | NOT NULL | 冗余便于查询 |
| strategy | VARCHAR(32) | NOT NULL | `turtle` / `bollinger_mean_reversion` |
| stock_code | VARCHAR(16) | FK→stocks | |
| signal | VARCHAR(8) | NOT NULL | `BUY` / `HOLD` / `AVOID` |
| score | NUMERIC(6,2) | NOT NULL | 0-100 |
| close | NUMERIC(12,4) | NOT NULL | **当日收盘价，必须冗余存储**，供模块三计算建议股数 |
| reason | TEXT | | 中文原因 |
| UNIQUE(strategy, run_date, stock_code) | | | 幂等 upsert 依据 |

## 索引

| 索引 | 列 | 说明 |
|---|---|---|
| idx_rec_query | (strategy, run_date, score DESC) | 推荐查询主路径（按策略+日期取高分），与 API 列表 `ORDER BY score DESC` 对齐，避免 filesort |
| idx_rec_stock | (stock_code, run_date) | 个股推荐回溯 / 模块三按持仓反查信号使用 |

## 说明

- 唯一约束以策略维度优先（`strategy, run_date, stock_code`），保证同策略同交易日无重复。
- **同一 `(run_date, stock_code)` 同日可存在多条策略记录**（海龟 + 布林带各占一行）；模块三须先按主文档 §5.4 的「多策略冲突聚合规则」合并出唯一全局信号，再进入场景映射。
- `close` 冗余存储：查询推荐列表时无需回联 `daily_bars`，且保证推荐值稳定不随行情变更漂移。
- 完整建表语句见 [DDL](../ddl.md)。

[← 返回 design.md](../../../design.md)
