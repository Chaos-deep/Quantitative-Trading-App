# 附录 · 数据库 · 行情与任务表

> 主文档：../../design.md · 版本随 v0.4 同步

## daily_bars（日线行情）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| stock_code | VARCHAR(16) | PK (FK→stocks) | 复合主键 |
| date | DATE | PK | 复合主键 |
| open / high / low / close | NUMERIC(12,4) | NOT NULL | |
| volume | NUMERIC(20,0) | NOT NULL | **单位：手** |
| amount | NUMERIC(20,2) | | 成交额 |

- 复合主键 `(stock_code, date)` 已覆盖查询索引，无需额外索引。

## strategy_runs（流水线任务）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | 即 run_id |
| strategy | VARCHAR(32) | NOT NULL | turtle / bollinger_mean_reversion |
| run_date | DATE | NOT NULL | |
| status | VARCHAR(16) | DEFAULT 'pending' | pending / running / success / failed |
| started_at / finished_at | TIMESTAMPTZ | | |
| stock_count | INT | | 处理数量 |
| note | TEXT | | 失败清单 / 错误信息 |
| 索引 | | | (strategy, run_date) |

## 说明

- `daily_bars` 采用批量 COPY / executemany 写入提升吞吐（见 [写入策略](../write-strategy.md)）。
- `strategy_runs` 状态更新统一归调度层负责，为未来迁移 Celery 预留（见 [流水线](../pipeline/overview.md)）。

[← 返回 design.md](../../../design.md)
