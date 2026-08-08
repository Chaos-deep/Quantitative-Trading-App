# 附录 · 数据库 · 写入策略

> 主文档：../../design.md · 版本随 v0.5 同步

## 写入总原则：全部幂等

全市场每日 5000+ 股票的流水线写入与重试必须幂等，任何一步可安全重跑而不产生脏数据。

| 写入点 | 方式 | 幂等依据 |
|---|---|---|
| stocks 增量更新 | upsert | 主键 `code` |
| daily_bars 批量写入 | 批量 COPY + ON CONFLICT DO NOTHING | `UNIQUE(stock_code, trade_date)` |
| recommendations | upsert | `UNIQUE(strategy, run_date, stock_code)` |
| user_personal_advice | upsert | `UNIQUE(user_id, stock_code, advice_date)` |
| user_positions | upsert | `UNIQUE(user_id, stock_code)` |

## 分表策略

- **daily_bars 只存日线**，不做分钟级存储；日线全市场约 5000 × 250 ≈ 125 万行/年，单表即可支撑，本期不分表。
- 扩容预留：当 daily_bars 体量达到千万级后，可按 `trade_date` 按月分区或归档，本期不实现。

## 存储成本约束

- 全市场日线拉取 + 双策略逐股计算，采用**逐股流式**处理（一次仅保留单股数据在内存），单批内存峰值约束在 **200MB 以内**（见 [模块二](../pipeline/overview.md)）。
- 批量 COPY 写入，避免逐行 INSERT 造成的连接与提交开销。

## 并发与一致性

- 写入全部发生在流水线后台任务中，API 层对 `recommendations` / `daily_bars` 只读。
- 流水线由 Redis 分布式锁保证单实例执行（见 [分布式锁](../pipeline/distributed-lock.md)）。

[← 返回 design.md](../../design.md)
