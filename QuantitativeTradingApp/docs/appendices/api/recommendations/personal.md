# 附录 · API · 个性化建议

> 主文档：../../design.md · 版本随 v0.4 同步

## GET /api/recommendations/personal

模块三（个性化投顾）产出的当前用户建议，默认 BUY/SELL 排 HOLD 前。

### 响应示例

```json
{
  "items": [
    {
      "stock_code": "600000.SH",
      "stock_name": "浦发银行",
      "advice_date": "2026-08-07",
      "action": "BUY",
      "suggested_shares": 200,
      "close": 8.15,
      "reason": "您未持有该股，今日海龟策略出现买入信号，建议按资金 5% 仓位买入 200 股"
    },
    {
      "stock_code": "000001.SZ",
      "stock_name": "平安银行",
      "advice_date": "2026-08-07",
      "action": "SELL",
      "suggested_shares": 1000,
      "close": 11.20,
      "reason": "您已持有该股，今日布林策略出现卖出信号，建议清仓全部 1000 股"
    }
  ],
  "total": 2,
  "page": 1,
  "limit": 50
}
```

### 排序 SQL（服务端约定，必须遵守）

```sql
SELECT *
FROM user_personal_advice
WHERE user_id = :uid AND advice_date = :date
ORDER BY CASE WHEN action='BUY' THEN 0
              WHEN action='SELL' THEN 1
              ELSE 2 END, id DESC
```

保证 BUY / SELL 优先于 HOLD。

### 说明

- 限流：每用户每分钟 60 次（见 [限流](../rate-limiting.md)）。
- `suggested_shares` 计算规则见 [模块三](../../design.md)。

[← 返回 design.md](../../../design.md)
