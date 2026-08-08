# 附录 · 流水线 · 每日调度时序

> 主文档：../../design.md · 版本随 v0.4 同步

## 每日流水线（17:00 Cron 触发）

```
17:00  Cron 触发
  │
  ├─ 0. 交易日判断（ak.tool_trade_date_hist_sina）：非交易日 → 记录 note='非交易日，跳过'、status=success，释放锁并退出（不报错、不拉数据）
  ├─ 1. Redis 获取分布式锁（失败则本轮跳过，另一实例已执行）
  ├─ 2. 创建 strategy_runs 记录（status=pending）
  ├─ 3. 模块一：拉取全 A 股代码列表，增量更新 stocks 表
  ├─ 4. 模块一：循环拉取日线（akshare → efinance 降级），批量 COPY 写入 daily_bars
  ├─ 5. 模块二：逐股流式运行策略一（海龟）→ 写 recommendations（含当日 close）
  ├─ 6. 模块二：逐股流式运行策略二（布林带均值回归）→ 写 recommendations（含当日 close）
  ├─ 7. 模块三：批量载入当日 recommendations + 全量持仓/偏好 → 内存计算 → upsert 写 user_personal_advice
  ├─ 8. 调度层更新 strategy_runs（status=success，记录数量/失败清单/耗时）
  └─ 9. Lua 脚本校验 run_id 后释放锁
```

## 职责边界

- **整条流水线由 `run_pipeline_core(run_id)` 承载**，状态更新归调度层负责。
- 该纯计算函数抽离是为未来迁移 Celery 预留：状态更新职责随 Worker 迁移，防止异步状态错乱。

## 内存约束

- 模块二（策略引擎）通过**逐股流式**处理：一次仅保留单股数据在内存，全市场计算后内存峰值约束在 **200MB 以内**。
- 模块三为内存批量计算（当日 recommendations + 全量持仓/偏好），需监控单日推荐量级。

[← 返回 design.md](../../design.md)
