# 附录 · 数据库 · stocks 表

> 主文档：../../design.md · 版本随 v0.4 同步

## 用途

全 A 股股票元信息，由模块一（数据工厂）增量维护。

## 表结构

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| code | VARCHAR(16) | PK | 如 `600000.SH` / `000001.SZ` |
| name | VARCHAR(64) | NOT NULL | |
| market | VARCHAR(16) | | `SH` / `SZ` / `BJ`，预留 `HK` / `US` |
| status | VARCHAR(16) | DEFAULT 'active' | `active` / `suspended` / `delisted` |
| updated_at | TIMESTAMPTZ | | 最后行情时间 |

## 说明

- 主键直接使用 `code` 字符串（`交易所.代码`），便于与行情数据直接 join。
- `market` 枚举预留港股/美股，本期仅使用 SH / SZ / BJ。
- 新上市/新出现股票自动入库；退市/停牌股票标记 `status`。
- 增量 upsert 保证幂等，见 [写入策略](../write-strategy.md)。

[← 返回 design.md](../../../design.md)
