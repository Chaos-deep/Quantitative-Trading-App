# 附录 · 流水线 · 失败处理与重试

> 主文档：../../design.md · 版本随 v0.5 同步

## 失败隔离原则

| 场景 | 处理 |
|---|---|
| 单股拉取失败 | 不阻断，记录日志 |
| 策略计算异常 | 记录到 note，单股异常不影响其余股票 |
| 模块三异常 | 不影响模块二结果（内存批量计算独立） |
| 非交易日 | status=success + note='非交易日，跳过'，不报错、不拉数据 |

## 重试机制

重试分两个层级，职责必须清晰：

- **全局调度层**（任务错过/中断的补跑）：由 APScheduler 的 **`misfire_grace_time=3600` + `coalesce=True`** 处理——若 17:00 任务因锁未获取或异常中断，允许 1 小时内补跑；`coalesce=True` 将多次触发合并为单次执行，防止重复入队。
- **数据获取层**（任务内部的单股失败）：按股票粒度循环重试（**最多 3 次**），akshare 失败则切 efinance 降级；重试不触发全局调度重跑。
- 模块三靠 upsert（`UNIQUE(user_id, stock_code, advice_date)`）保证重跑幂等。
- 全部写入点幂等，任何一步可安全重跑，见 [写入策略](../database/write-strategy.md)。

## 状态记录

- 流水线第 8 步更新 `strategy_runs`：status=success，记录处理数量（`stock_count`）、失败清单（写入 `note` 字段）、耗时（由 `started_at` / `finished_at` 计算）。
- 整条流水线由 `run_pipeline_core(run_id)` 承载，状态更新归调度层（在 `finally` 中执行），便于未来迁移 Celery。

[← 返回 design.md](../../design.md)
