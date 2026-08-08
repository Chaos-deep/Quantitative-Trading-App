# 附录 · 流水线 · 失败处理与重试

> 主文档：../../design.md · 版本随 v0.4 同步

## 失败隔离原则

| 场景 | 处理 |
|---|---|
| 单股拉取失败 | 不阻断，记录日志 |
| 策略计算异常 | 记录到 note，单股异常不影响其余股票 |
| 模块三异常 | 不影响模块二结果（内存批量计算独立） |
| 非交易日 | status=success + note='非交易日，跳过'，不报错、不拉数据 |

## 重试机制

- 同一任务最多重跑 **2 次**。
- 模块三靠 upsert（`UNIQUE(user_id, stock_code, advice_date)`）保证重跑幂等。
- 全部写入点幂等，任何一步可安全重跑，见 [写入策略](../database/write-strategy.md)。

## 状态记录

- 流水线第 8 步更新 `strategy_runs`：status=success，记录股票数量、失败清单（`failed_stock_list` JSONB）、耗时（`duration_seconds`）。
- 整条流水线由 `run_pipeline_core(run_id)` 承载，状态更新归调度层，便于未来迁移 Celery。

[← 返回 design.md](../../design.md)
