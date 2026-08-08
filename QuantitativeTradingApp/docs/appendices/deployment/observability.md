# 附录 · 部署 · 可观测性

> 主文档：../../design.md · 版本随 v0.5 同步

## 结构化日志

- 使用 **structlog** 输出 JSON 格式：时间、level、logger、run_id、stock_count、duration_seconds（由 `started_at`/`finished_at` 计算）、failed_stock_count（失败股票数；失败清单落库到 `strategy_runs.note`）。
- 每条 `strategy_runs` 执行结束时打印汇总指标，便于监控与检索。

## 请求追踪

- API 中间件为每次请求生成 **`X-Request-ID`**（写入响应头并贯穿日志）。
- 前端报错时凭该 ID 回溯后端日志。

## 日志滚动

- docker-compose 挂载 `./logs:/var/log/app`。
- 后端使用 `logging.handlers.TimedRotatingFileHandler` 按天滚动，保留 **7 天**。

[← 返回 design.md](../../design.md)
