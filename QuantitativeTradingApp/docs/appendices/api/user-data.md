# 附录 · API · 用户数据与元信息

> 主文档：../../design.md · 版本随 v0.5 同步

## POST /api/positions

新增/更新本人持仓（upsert）。

- 依据 `UNIQUE(user_id, stock_code)` 幂等。
- 请求体：`{ stock_code, shares, cost_price, buy_date }`；股票不存在返回 **404**。
- 返回：更新后的持仓记录（含 user_id、stock_code、shares、cost_price、buy_date）。
- 前端校验：股数 > 0、股票存在（调用 `/api/stocks/search`）。

## GET /api/preferences

查看本人风险偏好与总资金。

- 首次访问自动创建默认偏好（`risk_level=moderate`、`total_capital=null`）。

## PUT /api/preferences

更新本人风险偏好与总资金。

- 请求体：`{ risk_level, total_capital }`。
- `total_capital`、`risk_level` 为模块三仓位计算的输入，见 [模块三](../../design.md)。

## GET /api/strategies

可用策略元信息（策略名、说明等），供前端筛选器使用。

## GET /api/health

健康检查（含 DB 连通性），无需认证。

[← 返回 design.md](../../design.md)
