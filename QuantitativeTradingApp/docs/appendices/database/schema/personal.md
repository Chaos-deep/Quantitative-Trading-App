# 附录 · 数据库 · 个性化相关表

> 主文档：../../design.md · 版本随 v0.4 同步

## user_positions（用户持仓）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users | |
| stock_code | VARCHAR(16) | FK→stocks | |
| shares | INT | NOT NULL | 持有股数（**单位：股**，非手） |
| cost_price | NUMERIC(12,4) | | 成本价 |
| buy_date | DATE | | 买入日期 |
| UNIQUE(user_id, stock_code) | | | upsert 依据 |

## user_preferences（用户策略偏好）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| user_id | BIGINT | PK FK→users | 一用户一行（1:1） |
| risk_level | VARCHAR(16) | DEFAULT 'moderate' | `aggressive` / `moderate` / `conservative` |
| total_capital | NUMERIC(16,2) | | 总资金量（元），可为 NULL（视为未配置） |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

## user_personal_advice（个性化建议输出）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users | |
| stock_code | VARCHAR(16) | FK→stocks | |
| advice_date | DATE | NOT NULL | 建议日期 |
| action | VARCHAR(8) | NOT NULL | `BUY`（买入）/ `SELL`（卖出）/ `HOLD`（持有观望） |
| suggested_shares | INT | NOT NULL | 建议股数（BUY=加仓/买入量，SELL=清仓量，HOLD=0） |
| reason | TEXT | | 个性化理由 |
| UNIQUE(user_id, stock_code, advice_date) | | | 模块三 upsert 依据（幂等） |

## 索引

| 索引 | 列 | 说明 |
|---|---|---|
| idx_advice_user_date_action | (user_id, advice_date, action) | 我的建议列表查询（BUY/SELL 优先排序） |

## 说明

- `user_positions` / `user_preferences` 由用户通过 API 录入维护，建议依赖其准确性（前端校验股数 > 0、股票存在）。
- 模块三每日内存批量计算后按 `UNIQUE(user_id, stock_code, advice_date)` upsert，重跑幂等。

[← 返回 design.md](../../../design.md)
