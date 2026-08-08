# 图表组件（二期预留）

本期不实现，仅预留目录与接口约定。二期接入个股详情页（`GET /api/stocks/{code}/bars`）时在此实现 ECharts 封装：

- K 线图
- 成交量
- 技术指标

数据来源：`GET /api/stocks/{code}/bars?limit=500`，返回按日期升序的日线数组
（date / open / high / low / close / volume / amount）。
