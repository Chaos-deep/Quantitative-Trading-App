# 附录 · API · 用户数据与元信息

> 主文档：../../design.md · 版本随 v0.4 同步

## POST /api/positions

新增/更新本人持仓（upsert）。

- 依据 `UNIQUE(user_id, stock_code)` 幂等。
- 前端校验：股数 > 0、股票存在（调用 `/api/stocks/search`）。

## GET /api/preferences

查看本人风险偏好与总资金。

## PUT /api/preferences

更新本人风险偏好与总资金。

- `total_capital`、`risk_level` 为模块三仓位计算的输入，见 [模块三](../../design.md)。

## GET /api/strategies

可用策略元信息（策略名、说明等），供前端筛选器使用。

## GET /api/health

健康检查（含 DB 连通性），无需认证。

[← 返回 design.md](../../design.md)
