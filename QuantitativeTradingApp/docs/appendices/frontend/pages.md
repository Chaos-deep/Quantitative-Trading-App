# 附录 · 前端 · 页面结构

> 主文档：../../design.md · 版本随 v0.4 同步

## 技术栈

Next.js 14（App Router）+ TypeScript + Tailwind CSS + Zustand（轻量状态管理）+ SWR（数据请求）。

## 页面结构（第一期）

```
/                    → 重定向 /login 或 /recommendations
/login               → 登录页（含注册切换）
/recommendations     → 推荐列表页（受保护）
  ├─ Tabs：全局推荐（模块二）/ 我的建议（模块三）
  ├─ 全局推荐 Tab：
  │   ├─ 策略筛选（全部/海龟/布林均值回归）
  │   ├─ 日期选择器（默认最新交易日）
  │   ├─ 筛选：信号（BUY/HOLD/AVOID）
  │   └─ 表格列：策略/代码/名称/信号（颜色标签）/评分/原因
  ├─ 我的建议 Tab（默认 BUY 排前）：
  │   └─ 表格列：日期/代码/名称/操作（红=卖出、绿=买入标签）/建议股数/理由
  │       └─ 空态提示："暂无建议，请先在我的持仓页添加持仓"
  └─ 我的持仓/偏好入口（表单调用 POST /positions、GET/PUT /preferences）
```

## 约定

- 信号颜色标签：BUY=绿、SELL/HOLD=对应色；操作标签：买入=绿、卖出=红。
- 持仓/偏好录入表单需校验：股数 > 0、股票存在（调用 `/api/stocks/search`）。

[← 返回 design.md](../../design.md)
