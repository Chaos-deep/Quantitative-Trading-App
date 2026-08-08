# 附录 · 数据库 · 个性化相关表

> 主文档：../../../design.md · 版本随 v0.5 同步

## user_positions（用户持仓）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users | |
| stock_code | VARCHAR(16) | FK→stocks | |
| shares | INT | NOT NULL | 持有股数（**单位：股**，非手；A 股 1 手 = 100 股，禁止混用） |
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
| suggested_shares | INT | NOT NULL | 建议股数（**单位：股**；BUY=加仓/买入量，SELL=清仓量，HOLD=0） |
| reason | TEXT | | 个性化理由 |
| strategy_signals | JSONB | NOT NULL DEFAULT '[]' | 当日该股各策略原始信号，数组 of 对象：`[{"strategy":"turtle","signal":"BUY"},{"strategy":"bollinger_mean_reversion","signal":"AVOID"}]`；`strategy` 用规范名，聚合前的原始记录 |
| UNIQUE(user_id, stock_code, advice_date) | | | 模块三 upsert 依据（幂等） |

## 索引

| 索引 | 列 | 说明 |
|---|---|---|
| idx_advice_user_date_action | (user_id, advice_date, action) | 我的建议列表查询（BUY/SELL 优先排序） |

## 说明

- `user_positions` / `user_preferences` 由用户通过 API 录入维护，建议依赖其准确性（前端校验股数 > 0、股票存在）。
- 模块三每日内存批量计算后按 `UNIQUE(user_id, stock_code, advice_date)` upsert，重跑幂等。
- `strategy_signals` 在模块三聚合时生成：先逐策略记录原始 `signal`，再按主文档 §5.4「多策略冲突聚合规则」折叠出全局 `action`；`strategy` 键与 `recommendations.strategy` 取值一致（`turtle` / `bollinger_mean_reversion`）。

[← 返回 design.md](../../../design.md)
