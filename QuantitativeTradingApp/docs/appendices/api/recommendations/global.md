# 附录 · API · 全局推荐

> 主文档：../../design.md · 版本随 v0.4 同步

## GET /api/recommendations/global

模块二（策略引擎）产出推荐列表。

### 查询参数

| 参数 | 类型 | 说明 |
|---|---|---|
| strategy | string | turtle / bollinger_mean_reversion，缺省返回全部 |
| date | date | 指定交易日，缺省最新 |
| signal | string | BUY/HOLD/AVOID 过滤 |
| limit / offset | int | 分页，limit 默认 50 |
| order_by | string | score 等，默认 score desc |

### 响应示例

```json
{
  "items": [
    {
      "stock_code": "600000.SH",
      "stock_name": "浦发银行",
      "strategy": "turtle",
      "run_date": "2026-08-07",
      "signal": "BUY",
      "score": 82.5,
      "reason": "收盘价突破55日高点，量能放大1.8倍，20日均线上行"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 50
}
```

### 说明

- 主查询路径 `WHERE strategy=? AND run_date=? ORDER BY score DESC LIMIT ?` 由 `idx_rec_query` 完全命中。
- `stock_name` 需回联 `stocks` 表。
- 限流：每用户每分钟 60 次（见 [限流](../rate-limiting.md)）。

[← 返回 design.md](../../../design.md)
