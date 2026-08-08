# 附录 · API · 股票查询

> 主文档：../../design.md · 版本随 v0.5 同步

## GET /api/stocks/search

模糊搜索股票代码/名称。

- 参数：`q`（必填）、`limit`（可选，默认 20，上限 **50**）。
- 返回：匹配的股票列表（code、name、market），按 code 升序。
- 用于持仓/偏好录入时的股票存在性校验。

## GET /api/stocks/{code}/bars

个股日线（二期详情页使用，本期已提供）。

- `code` 不存在返回 **404**。
- 参数：`limit`（可选，默认 120，上限 **500**）。
- 返回：该股按日期升序的日线数据。

[← 返回 design.md](../../design.md)
