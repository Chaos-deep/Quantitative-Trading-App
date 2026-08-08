# A股量化选股系统 · 设计文档

> **Agent 使用指引**：本文档为系统唯一主文档。**交付时必须包含整个 `docs/` 目录（含全部 `docs/appendices/` 子目录）**，Agent 须按相对路径读取所有被引用的附录文件——只发送 `design.md` 单文件会导致附录缺失而无法编码。正文 §1-§7 与附录 `appendices/database/`、`appendices/api/`、`appendices/pipeline/` 构成**最低可执行子集**（后端骨架可直接按此交付）；其中三块必须严格照抄的可执行内容位于：DDL 建表语句 → `appendices/database/ddl.md`、JWT 黑名单流程 → `appendices/api/auth/jwt.md`、Redis Lua 锁脚本 → `appendices/pipeline/distributed-lock.md`；前端、部署、目录、风险与策略参考按需查阅对应附录。所有附录文件页眉标注「版本随 v0.5 同步」，与本主文档保持一致；文档间链接一律为相对路径，移动文件时需同步更新。

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 文档名称 | A股量化选股系统设计文档 |
| 版本号 | v0.5 |
| 状态 | 草稿（Draft） |
| 创建日期 | 2026-08-08 |
| 最后更新 | 2026-08-08 |
| 作者 | 待填写 |

### 版本变更纪要

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-08-08 | 初始版本：确定整体架构、技术选型、双策略规则、数据库 Schema、API 设计、部署方案 | 待填写 |
| v0.2 | 2026-08-08 | 生产健壮性优化：JWT 严格黑名单吊销、Redis 锁 Lua 原子释放、策略逐股流式处理、recommendations 索引优化、Celery 迁移路径修正、API 限流、交易日判断、可观测性 | 待填写 |
| v0.3 | 2026-08-08 | 新增模块三（用户个性化投顾）：user_positions/user_preferences/user_personal_advice 三表、recommendations 增加 close 列、/recommendations/global 与 /personal 路由、持仓/偏好管理接口、refresh 防重放、限流 XFF 信任、前端双 Tab | 待填写 |
| v0.4 | 2026-08-08 | 文档重构：正文精简为 §1-§7，详细规范拆分为 `docs/appendices/` 分层附录（database/api/pipeline/frontend/deployment/structure/risks/turtle），原 agent_instruction.md 内容并入 §6 与相关附录并删除该文件，附录以相对路径索引 | 待填写 |
| v0.5 | 2026-08-08 | 逻辑修复：统一 shares/suggested_shares 单位为"股"并强化 §6 单位约束（1 手 = 100 股）；新增模块三多策略冲突聚合规则（风险优先）；`user_personal_advice` 新增 `strategy_signals`（JSONB）字段记录每股各策略原始信号；确认打包交付 `docs/` 全目录给 Agent 并强化使用指引；JWT 刷新补齐含 `ver` 的严格检查顺序；调度层补 APScheduler misfire/coalesce + 单股重试机制 | 待填写 |

> **版本变更规范**：每当文档发生实质性变更（新增/修改模块、调整架构、变更技术选型），必须在上述表格追加一行，记录版本号、日期、变更摘要与作者。版本号遵循语义化版本（主版本.次版本.修订号）。

### 附录索引

```
docs/
├── design.md               # 本文档（主文档）
└── appendices/
    ├── database/           # 附录 · 数据库
    │   ├── schema/         #   表结构
    │   │   ├── users.md
    │   │   ├── stocks.md
    │   │   ├── market-data.md        # daily_bars + strategy_runs
    │   │   ├── recommendations.md
    │   │   └── personal.md           # user_positions / user_preferences / user_personal_advice
    │   ├── ddl.md          #   建表语句 + 命名索引
    │   └── write-strategy.md         #   写入策略（幂等 / 分表 / 存储成本）
    ├── api/                # 附录 · API 规范
    │   ├── auth/
    │   │   ├── jwt.md      #   令牌模型 + 严格黑名单 + 防重放
    │   │   └── endpoints.md
    │   ├── recommendations/
    │   │   ├── global.md   #   查询参数 + 响应示例
    │   │   └── personal.md #   排序 SQL + 响应示例
    │   ├── stocks.md       #   stocks/search、stocks/{code}/bars
    │   ├── user-data.md    #   positions / preferences / strategies / health
    │   └── rate-limiting.md        #   限流 + XFF 信任
    ├── pipeline/           # 附录 · 调度流水线
    │   ├── overview.md     #   0-9 步时序 + 职责边界
    │   ├── distributed-lock.md     #   Lua 原子释放
    │   └── failure-handling.md     #   失败处理与重试
    ├── frontend/           # 附录 · 前端
    │   ├── pages.md        #   页面结构与双 Tab
    │   ├── state.md        #   Zustand/SWR + refreshAttempted 防死循环
    │   └── charts.md       #   图表预留
    ├── deployment/         # 附录 · 部署
    │   ├── topology.md     #   服务拓扑
    │   ├── environment.md  #   环境变量清单
    │   ├── startup.md      #   启动流程
    │   ├── seed.md         #   种子脚本
    │   └── observability.md       #   可观测性
    ├── structure/
    │   └── tree.md         #   项目目录树
    ├── risks/
    │   └── register.md     #   风险登记表
    └── turtle/             # 附录 · 策略参考（海龟交易法则）
        ├── overview.md     #   起源 / 哲学
        ├── indicators.md   #   N值(ATR) / 唐奇安通道
        ├── rules.md        #   入场 / 加仓 / 止损 / 离市
        ├── position-sizing.md
        ├── summary-adaptation.md   # 总结 / A股适用性
        ├── quick-reference.md      # 参数速查 / 实盘注意事项
        └── code.md         #   核心代码实现
```

---

## 2. 项目概述

**目标**：构建一套 A 股日线量化选股系统。每日自动获取全市场 A 股日线数据，运行多策略引擎（海龟交易、布林带均值回归）产生全局股票推荐评分，并为 1 万独立注册用户生成个性化投资建议（结合其持仓、总资金与风险偏好），通过 Web 应用（浏览器访问）向登录用户展示。

**系统边界**（三大模块）：

- 模块一（数据工厂）：A 股数据获取（akshare 主 + efinance 备），适配器模式，`market` 参数当前支持 SH/SZ/BJ（预留 HK/US）。
- 模块二（全局公共推荐）：每日定时运行双策略，产出全市场 5000+ 只股票的 BUY/HOLD/AVOID 信号，结果对所有用户一致。
- 模块三（用户个性化投顾）：针对每个用户，结合已持仓 + 总资金 + 风险偏好，生成专属 BUY/SELL/HOLD 建议（含建议股数）。

**第一期范围**：
- 每日定时全市场数据获取（akshare 主 + efinance 备用）
- 双策略引擎（海龟 / 布林带均值回归）
- 用户个性化投顾引擎（模块三）
- FastAPI 提供 REST API（JWT 认证 + 限流）
- Next.js Web 应用：登录页 + 推荐列表页（全局/我的双 Tab + 持仓/偏好管理入口）
- Docker Compose + Nginx 部署

**非目标（本期不做）**：分钟线/实时行情、个股 K 线详情页（二期）、自选股社区、移动端、Celery 分布式任务队列、港股美股行情接入。

---

## 3. 系统架构

```
┌─────────────────────────────── 后端（模块一/二/三） ───────────────────────────────┐
│                                                                                    │
│  [APScheduler 定时任务]  17:00 触发，Redis Lua 分布式锁 + 交易日判断                  │
│         │                                                                          │
│         ▼                                                                          │
│  [模块一·数据获取层]  akshare(主) → efinance(备) 自动降级，适配器模式 market=SH/SZ/BJ │
│         │  全 A 股日线                                                             │
│         ▼                                                                          │
│  [数据存储]  PostgreSQL (daily_bars / stocks / strategy_runs)                       │
│         │                                                                          │
│         ▼                                                                          │
│  [模块二·策略引擎]  Pandas + NumPy，逐股流式  海龟 / 布林带 → recommendations       │
│         │                                                                          │
│         ▼                                                                          │
│  [模块三·个性化投顾]  user_positions + user_preferences + recommendations(close)    │
│         │  → user_personal_advice（内存批量计算，upsert）                            │
│         ▼                                                                          │
│  [FastAPI 接口层]  /api/...  JWT 认证 + 限流(XFF)                                  │
└────────────┬───────────────────────────────────────────────────────────────────────┘
             │  HTTP + JSON
             ▼
┌────────────┴───────────────────────────────────────────────────────────────────────┐
│                            前端（Web）                                              │
│                                                                                    │
│  [Next.js 14 + TypeScript + Tailwind + Zustand + SWR]                              │
│      登录页 → JWT → 推荐列表页                                                      │
│        ├─ 全局推荐 Tab：策略/日期/信号筛选、评分/信号/原因                            │
│        └─ 我的建议 Tab：BUY/SELL 优先、红绿标签、建议股数                            │
│      持仓/偏好管理入口；401 自动刷新（refreshAttempted 防死循环）                    │
│      （预留 ECharts 组件目录，二期接入 K 线详情）                                    │
└────────────────────────────────────────────────────────────────────────────────────┘

             Nginx 反代：/ → Next.js，/api → FastAPI；透传 X-Forwarded-For / X-Request-ID
```

---

## 4. 技术选型

| 层级 | 选型 | 理由 |
|---|---|---|
| 数据源 | akshare（主）+ efinance（备） | 免费开源、东方财富/新浪/腾讯多源、社区活跃；efinance 轻量降级 |
| 策略引擎 | Python 3.11 + Pandas + NumPy | 自建轻量引擎，逻辑清晰可控，无需重型回测框架 |
| API 框架 | FastAPI + Pydantic + slowapi | 高性能、异步、自动 Swagger 文档、原生 JSON；slowapi 提供基于 Redis 的限流 |
| 数据库 | PostgreSQL 16（`postgres:16-alpine`） | 数据持久化，支持索引与批写入；**本期不引入 pgvector** |
| ORM/迁移 | SQLAlchemy 2.0 + Alembic | 类型安全、迁移可追踪 |
| 认证 | JWT（python-jose + passlib/bcrypt） | 无状态、前后端分离友好 |
| 调度 | APScheduler + Redis 分布式锁 | 初期最小化；演进路径见 §5.3 |
| 前端 | Next.js 14 + TypeScript + Tailwind CSS + Zustand + SWR | 全栈 React、类型安全、SSR、轻量状态与请求缓存 |
| 图表 | ECharts（预留） | K 线/技术指标行业标准 |
| 部署 | Docker Compose + Nginx | 容器化、单机多服务编排 |

---

## 5. 模块设计

### 5.1 数据工厂（模块一）

- **主数据源**：akshare。获取接口：
  - 股票列表：`ak.stock_info_a_code_name()`（全 A 股代码/名称）
  - 日线：`ak.stock_zh_a_hist(symbol, period="daily", start_date, end_date, adjust="qfq")`
  - 交易日历：`ak.tool_trade_date_hist_sina()`（交易日判断）
- **备用数据源**：efinance。当日线获取异常时自动降级，保障可用性。
- **降级策略**：按股票粒度重试 → 切备用源 → 记录失败清单（写入日志与 `strategy_runs.note`），不阻断整体流程。
- **全市场覆盖**：约 5000+ 只股票，预计拉取耗时 10-30 分钟，接受慢速但必须全覆盖。
- 新上市/新出现股票自动入库到 `stocks` 表；退市/停牌股票标记 `status`。

### 5.2 策略引擎（模块二，自建 Pandas + NumPy）

统一接口约定：每个策略实现 `run(daily_bars: DataFrame) -> list[Recommendation]`，输出 `score`（0-100）、`signal`（BUY/HOLD/AVOID）、`reason`（中文原因摘要）。策略以插件形式注册（`STRATEGY_REGISTRY`），新增策略只需实现统一接口并注册，不影响调度与 API 层；策略配置（参数、阈值）全部外置到 `config`。

#### 策略一：海龟交易（趋势跟踪）

| 项目 | 规则 |
|---|---|
| 入场 | 收盘价突破 20 日最高价（System 1）/ 55 日最高价（System 2） |
| 出场 | 收盘价跌破 10 日（System 1）/ 20 日（System 2）最低价 |
| 波动过滤 | ATR(20) < 近 60 日均量对应阈值时跳过（过滤低波动/无量标的） |
| 额外过滤 | 排除 ST、上市不足 60 日、停牌 |
| 评分构成 | 突破强度（价格/突破位）、趋势斜率（20 日均线方向）、量能配合（突破日成交量 / 5 日均量） |
| 信号 | 满足突破 → BUY；持仓中未破位 → HOLD；破位 → AVOID |

> 海龟法则完整理论（N 值/ATR、唐奇安通道、加仓/止损/离市规则、A 股适用性改造）见 [策略参考·海龟交易法则](appendices/turtle/overview.md)。

#### 策略二：布林带均值回归（与趋势跟踪互补，覆盖震荡市）

| 项目 | 规则 |
|---|---|
| 参数 | 中轨 MA(20)，带宽 2×STD(20) |
| 入场 | 收盘价触及或跌破下轨，且 RSI(14) < 30 |
| 出场 | 价格反弹回中轨，或 RSI(14) > 50 |
| 风险过滤 | 排除 ST；排除趋势性下跌（收盘价低于年线 MA(250) 20% 以上） |
| 评分构成 | 乖离率（下轨偏离程度）、RSI 超卖程度、缩量止跌信号（量能萎缩 + 下影线） |
| 信号 | 触发 → BUY；回中轨 → HOLD；RSI 回升但价格走弱 → AVOID |

**内存与性能约束**：全市场 5000+ 只股票日线累计数千万行，严禁将全表 `daily_bars` 一次性加载至 Pandas DataFrame（内存占用可达 500MB~1GB，有 OOM 风险）。策略引擎必须采用**逐股流式处理**：遍历 `stocks` 表，单次仅查询当前股票的历史 K 线序列（`ORDER BY date DESC LIMIT 500`，足够覆盖 MA(250)、ATR(60) 等指标窗口），计算指标生成推荐后立即释放该 DataFrame 对象，再处理下一只。此举可将进程内存占用恒定控制在 200MB 以内，且单股计算异常不影响其余股票。

### 5.3 调度层（模块三载体 + APScheduler + Redis 分布式锁）

- **触发**：每日 17:00（Asia/Shanghai，收盘后）Cron 触发。
- **分布式锁**：Redis `daily_pipeline_lock`，Value = `uuid.uuid4()`，`SET NX EX 7200`；获取锁成功才执行，防止多实例重复运行。**释放锁必须用 Lua 脚本校验 Value（run_id/uuid）匹配才删除**，禁止裸 `DEL`（否则任务超时后可能误删其他实例刚获取的新锁，导致双实例并发现象）。Lua 脚本与完整 0-9 步流水线时序见 [流水线附录](appendices/pipeline/overview.md)。
- **执行入口**：`run_pipeline_core(run_id)` 为唯一重计算入口（**纯业务计算，不涉及 `strategy_runs` 状态更新**），内部依次：交易日判断 → 拉全市场数据 → 写库 → 跑策略 → 写推荐 → 模块三批量计算 → 状态更新由调度层在 `finally` 中完成（success/failed，记录数量/失败清单/耗时）。
- **演进路径（避免异步状态不一致）**：核心计算逻辑已抽取为独立函数 `run_pipeline_core(run_id)`，与"执行状态管理"完全剥离：
  - **APScheduler 阶段**：调度器同步调用 `run_pipeline_core`，在 `finally` 中更新 `strategy_runs` 状态并释放锁。
  - **迁移 Celery 阶段**：APScheduler 仅改为 `run_pipeline_core.delay(run_id)`（异步投递）。**关键注意**：`delay()` 会瞬间返回，此时必须在 Celery Worker 内部（或 `after_return` 回调）自行更新 `strategy_runs` 状态；调度层绝不能因 `delay()` 立即返回就误判任务执行成功，否则状态会错乱为 success。
  - 初期切莫过度设计，仅做上述结构预留。
- **重试机制（必须遵守）**：全局调度重试由 APScheduler 的 `misfire_grace_time=3600` + `coalesce=True` 处理——若 17:00 任务因锁未获取或异常中断，允许 1 小时内补跑，且多次触发合并为单次执行（防止重复入队）。任务内部（如单股拉取失败）在数据获取层按股票粒度循环重试（最多 3 次），不触发全局调度重跑；模块三写入靠 upsert 保证重试幂等。

### 5.4 用户个性化投顾（模块三）

**输入**：用户持仓（`user_positions`）+ 风险偏好/总资金（`user_preferences`）+ 当日全局推荐（`recommendations`，含 `close` 收盘价）。**输出**：`user_personal_advice`（action + suggested_shares + reason + strategy_signals）。

**计算方式**：不得逐用户重复查库（1 万用户 × 多次查询 = 3 万+ 次 DB 往返）。一次性批量加载当日全部 `recommendations`（含 close）、全量 `user_positions`、全量 `user_preferences`，在内存中完成所有用户计算后统一写入。

**建议生成规则**（按场景映射）：

| 场景 | 全局信号 | action | suggested_shares | 理由模板 |
|---|---|---|---|---|
| 已持仓 | BUY | HOLD | 加仓量 `floor(总资金 × 5% / close / 100) × 100`；< 100 则为 0 | "您已持有该股，今日出现买入信号，建议持有并可加仓 N 股" |
| 已持仓 | HOLD | HOLD | 0 | "您已持有该股，今日信号为持有，建议继续持有" |
| 已持仓 | AVOID | SELL | 当前持仓股数（清仓） | "您已持有该股，今日出现卖出信号，建议清仓全部 N 股" |
| 未持仓 | BUY | BUY | 同上公式；**< 100（买不起 1 手）则跳过不生成** | "您未持有该股，今日出现买入信号，建议按资金 5% 仓位买入 N 股" |
| 未持仓 | HOLD / AVOID | 不生成 | — | — |

**多策略冲突聚合规则（必须实现）**：同一 `(run_date, stock_code)` 在 `recommendations` 中可能对应多条策略记录（海龟 + 布林带）。模块三在内存批量加载当日推荐后，**先为每股生成 `strategy_signals`（数组 of 对象，逐策略记录原始 `signal`，`strategy` 用规范名 `turtle` / `bollinger_mean_reversion`，如 `[{"strategy":"turtle","signal":"BUY"},{"strategy":"bollinger_mean_reversion","signal":"AVOID"}]`，供前端展示各策略信号）**，再按以下规则聚合出唯一的"全局信号"，进入上方场景映射表：

1. 若存在任一策略输出 `AVOID` → 该股全局信号统一为 `AVOID`（风险优先，保护本金）。
2. 若不存在 `AVOID`，但存在任一策略输出 `BUY` → 全局信号为 `BUY`。
3. 仅当全部策略输出均为 `HOLD` → 全局信号为 `HOLD`。
4. `score` 取各策略评分的平均值（用于前端排序）；`reason` 拼接多条策略理由（格式：`"海龟：突破；布林：超卖"`）。

**约束**：`total_capital` 为 NULL 或未配置偏好时不生成 BUY（已持仓场景照常生成 HOLD/SELL）；写入采用 **upsert**（按 `UNIQUE(user_id, stock_code, advice_date)` 覆盖），保证流水线重跑/重试幂等；持仓反查依赖 `idx_rec_stock (stock_code, run_date)`（见 [数据库附录](appendices/database/schema/recommendations.md)）。

**一期输入通道**：提供 `POST /positions`（upsert 本人持仓）与 `GET/PUT /preferences`（本人风险偏好/总资金）接口 + 种子脚本示例用户，保证模块三可产出可验证（见 [部署附录·seed](appendices/deployment/seed.md)）。

---

## 6. 编码硬性约束速览

Agent / 开发者违反以下任一条必然产生 bug，编码时必须逐条核对：

- **内存约束**：严禁 `SELECT * FROM daily_bars` 一次性加载全量。模块二必须**逐股流式处理**（循环股票代码，单次仅查该股最近 500 条 K 线，计算完立即释放 DataFrame），内存峰值 ≤200MB；模块三禁止逐用户查库，必须**批量加载**当日推荐 + 全量持仓/偏好到内存计算。
- **分布式锁约束**：Redis 锁 `daily_pipeline_lock`，Value = `uuid.uuid4()`，TTL 7200s；**释放必须用 Lua 脚本**校验 Value 匹配才删除，禁止裸 `DEL`（脚本见 [分布式锁附录](appendices/pipeline/distributed-lock.md)）。
- **JWT 严格黑名单（语义必须自洽）**：登录不存任何会话状态；**登出 = 将 jti 写入 Redis 黑名单（不是删除）**；**刷新必须严格按顺序执行：① 验签 → ② 解码提取 `jti` 与 `ver` → ③ 查 Redis 黑名单（`jti` 存在即拒绝）→ ④ 查 `user:{id}:token_version` 是否等于 `ver`（不等则立即拒绝，返回 401）→ ⑤ 全部通过后轮换新 token，并将旧 `jti` 写入黑名单**（顺序不可颠倒）；全设备踢出靠 `ver` 声明 + `user:{id}:token_version` 递增（详见 [JWT 附录](appendices/api/auth/jwt.md)）。
- **限流 XFF 信任**：login 按真实客户端 IP 限流（5 次/分钟）；`/recommendations/global` 与 `/recommendations/personal` 按用户限流（各 60 次/分钟）；**必须信任 Nginx 透传的 X-Forwarded-For**（详见 [限流附录](appendices/api/rate-limiting.md)）。
- **幂等约束**：`user_personal_advice` 设 `UNIQUE(user_id, stock_code, advice_date)`、`recommendations` 设 `UNIQUE(strategy, run_date, stock_code)`，流水线重跑/重试一律 **upsert**（详见 [写入策略附录](appendices/database/write-strategy.md)）。
- **时区约束**：所有定时任务、日期存储统一 `Asia/Shanghai`；调度触发与 `run_date` / `advice_date` 均以该时区为准。
- **单位与命名约束**：所有持仓/建议股数字段（`shares` / `suggested_shares`）单位一律为**股**，禁止与**手**混用（A 股 1 手 = 100 股，混用会导致清仓/加仓数量缩小 100 倍）；仅 `daily_bars.volume` 保留**手**以对齐 akshare 数据源；DDL 命名一律 `snake_case`，索引按 `idx_` 前缀（见 [DDL 附录](appendices/database/ddl.md)）。
- **范围约束**：本期不引入 pgvector（镜像 `postgres:16-alpine`，不加 `CREATE EXTENSION`）；`market` 枚举当前仅 SH/SZ/BJ，预留 HK/US 本期不实现。

---

## 7. 里程碑计划

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| M1 后端跑通 | 模块一数据层 + 模块二策略引擎 + 模块三投顾 + 调度 + API | 手动触发流水线，全市场数据入库，双策略产出推荐，个性化建议可生成，`/api/recommendations/global` 与 `/personal` 返回 JSON |
| M2 前端联调 | 登录 + 推荐列表页（双 Tab + 持仓/偏好入口） | 登录后展示全局推荐与个性化建议，筛选/排序可用 |
| M3 部署 | Docker Compose + Nginx | 一键启动，Nginx 正确路由，每日定时任务自动运行 |
| M4（二期） | 个股详情 K 线、自选股、图表增强 | 未排期 |

---

> **执行顺序建议**：先交付 backend 骨架（模型 + 迁移 + 认证 + 锁 + 流水线 + 策略 + 投顾）并跑通，再交付前端；若单次任务量过大，按 `Step 1: 模块一 + 认证` → `Step 2: 模块二` → `Step 3: 模块三` → `Step 4: 前端` 分步补齐。

> 风险与待定事项登记表见 [风险附录](appendices/risks/register.md)。
