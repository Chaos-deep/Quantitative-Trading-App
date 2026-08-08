# A股量化选股系统 · 设计文档

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 文档名称 | A股量化选股系统设计文档 |
| 版本号 | v0.1 |
| 状态 | 草稿（Draft） |
| 创建日期 | 2026-08-08 |
| 最后更新 | 2026-08-08 |
| 作者 | 待填写 |

### 版本变更纪要

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-08-08 | 初始版本：确定整体架构、技术选型、双策略规则、数据库 Schema、API 设计、部署方案 | 待填写 |

> **版本变更规范**：每当文档发生实质性变更（新增/修改模块、调整架构、变更技术选型），必须在上述表格追加一行，记录版本号、日期、变更摘要与作者。版本号遵循语义化版本（主版本.次版本.修订号）。

---

## 2. 项目概述

**目标**：构建一套 A 股日线量化选股系统。每日自动获取全市场 A 股日线数据，运行多策略引擎（海龟交易、布林带均值回归）产生股票推荐评分，通过 Web 应用（浏览器访问）向登录用户展示推荐列表。

**系统边界**：

- 模块一（后端）：数据获取 → 策略计算 → JSON 输出
- 模块二（前端）：接收 JSON → App 展示

**第一期范围**：
- 每日定时全市场数据获取（akshare 主 + efinance 备用）
- 双策略引擎（海龟 / 布林带均值回归）
- FastAPI 提供 REST API（JWT 认证）
- Next.js Web 应用：登录页 + 推荐列表页（表格展示）
- Docker Compose + Nginx 部署

**非目标（本期不做）**：分钟线/实时行情、个股 K 线详情页（二期）、自选股、移动端、Celery 分布式任务队列。

---

## 3. 系统架构

```
┌─────────────────────────────── 模块一：后端 ───────────────────────────────┐
│                                                                            │
│  [APScheduler 定时任务]                                                    │
│         │ 17:00 触发，Redis SET NX 分布式锁                                 │
│         ▼                                                                  │
│  [数据获取层]  akshare(主) → efinance(备) 自动降级                           │
│         │  全 A 股日线                                                     │
│         ▼                                                                  │
│  [数据存储]  PostgreSQL (daily_bars / stocks / strategy_runs)              │
│         │                                                                  │
│         ▼                                                                  │
│  [策略引擎]  Pandas + NumPy  海龟策略 / 布林带均值回归                       │
│         │                                                                  │
│         ▼                                                                  │
│  [FastAPI 接口层]  /api/recommendations 等，JWT 认证                        │
└────────────┬───────────────────────────────────────────────────────────────┘
             │  HTTP + JSON
             ▼
┌────────────┴───────────────────────────────────────────────────────────────┐
│                            模块二：前端（Web）                              │
│                                                                            │
│  [Next.js 14 + TypeScript + Tailwind]                                      │
│      登录页 → JWT → 推荐列表页（策略/日期筛选、评分/信号/原因）                │
│      （预留 ECharts 组件目录，二期接入 K 线详情）                            │
└────────────────────────────────────────────────────────────────────────────┘

             Nginx 反代：/ → Next.js，/api → FastAPI
```

---

## 4. 技术选型

| 层级 | 选型 | 理由 |
|---|---|---|
| 数据源 | akshare（主）+ efinance（备） | 免费开源、东方财富/新浪/腾讯多源、社区活跃；efinance 轻量降级 |
| 策略引擎 | Python 3.11 + Pandas + NumPy | 自建轻量引擎，逻辑清晰可控，无需重型回测框架 |
| API 框架 | FastAPI + Pydantic | 高性能、异步、自动 Swagger 文档、原生 JSON |
| 数据库 | PostgreSQL 16 | 数据持久化，支持索引与批写入 |
| ORM/迁移 | SQLAlchemy 2.0 + Alembic | 类型安全、迁移可追踪 |
| 认证 | JWT（python-jose + passlib/bcrypt） | 无状态、前后端分离友好 |
| 调度 | APScheduler + Redis 分布式锁 | 初期最小化；见 §7 演进路径 |
| 前端 | Next.js 14 + TypeScript + Tailwind CSS | 全栈 React、类型安全、SSR |
| 图表 | ECharts（预留） | K 线/技术指标行业标准 |
| 部署 | Docker Compose + Nginx | 容器化、单机多服务编排 |

---

## 5. 模块一设计（后端）

### 5.1 数据获取层

- **主数据源**：akshare。获取接口：
  - 股票列表：`ak.stock_info_a_code_name()`（全 A 股代码/名称）
  - 日线：`ak.stock_zh_a_hist(symbol, period="daily", start_date, end_date, adjust="qfq")`
- **备用数据源**：efinance。当日线获取异常时自动降级，保障可用性。
- **降级策略**：按股票粒度重试 → 切备用源 → 记录失败清单（写入日志与 `strategy_runs` 的 note 字段），不阻断整体流程。
- **全市场覆盖**：约 5000+ 只股票，预计拉取耗时 10-30 分钟，接受慢速但必须全覆盖。
- 新上市/新出现股票自动入库到 `stocks` 表；退市/停牌股票标记状态。

### 5.2 策略引擎（自建，Pandas + NumPy）

统一接口约定：每个策略实现 `run(daily_bars: DataFrame) -> list[Recommendation]`，输出 `score`（0-100）、`signal`（BUY/HOLD/AVOID）、`reason`（中文原因摘要）。策略配置（参数、阈值）全部外置到 `config`。

#### 策略一：海龟交易（趋势跟踪）

| 项目 | 规则 |
|---|---|
| 入场 | 收盘价突破 20 日最高价（System 1）/ 55 日最高价（System 2） |
| 出场 | 收盘价跌破 10 日（System 1）/ 20 日（System 2）最低价 |
| 波动过滤 | ATR(20) < 近 60 日均量对应阈值时跳过（过滤低波动/无量标的） |
| 额外过滤 | 排除 ST、上市不足 60 日、停牌 |
| 评分构成 | 突破强度（价格/突破位）、趋势斜率（20 日均线方向）、量能配合（突破日成交量 / 5 日均量） |
| 信号 | 满足突破 → BUY；持仓中未破位 → HOLD；破位 → AVOID |

#### 策略二：布林带均值回归（与趋势跟踪互补，覆盖震荡市）

| 项目 | 规则 |
|---|---|
| 参数 | 中轨 MA(20)，带宽 2×STD(20) |
| 入场 | 收盘价触及或跌破下轨，且 RSI(14) < 30 |
| 出场 | 价格反弹回中轨，或 RSI(14) > 50 |
| 风险过滤 | 排除 ST；排除趋势性下跌（收盘价低于年线 MA(250) 20% 以上） |
| 评分构成 | 乖离率（下轨偏离程度）、RSI 超卖程度、缩量止跌信号（量能萎缩 + 下影线） |
| 信号 | 触发 → BUY；回中轨 → HOLD；RSI 回升但价格走弱 → AVOID |

**设计原则**：策略以插件形式注册（`STRATEGY_REGISTRY`），新增策略只需实现统一接口并注册，不影响调度与 API 层。

### 5.3 调度层（APScheduler + Redis 分布式锁）

- **触发**：每日 17:00（收盘后）Cron 触发。
- **分布式锁**：Redis `SET lock_key run_id NX EX 7200`，获取锁成功才执行，防止多实例重复运行；执行结束或超时释放。
- **执行入口**：`do_heavy_computation(run_id)` 为唯一重计算入口，内部依次：拉全市场数据 → 写库 → 跑策略 → 写推荐结果。
- **演进路径（文档预留）**：当系统需要上百种定时任务、按优先级分队列时，将调度层平滑迁移至 Celery——仅把 `do_heavy_computation` 函数体改为 `send_task_to_celery.delay(run_id)`，调度层其余代码零改动。初期切莫过度设计。

---

## 6. 数据库设计

### 6.1 ER 概览

```
users ──────────────►  (认证)
stocks ◄─────────── daily_bars   (stocks.code ← daily_bars.stock_code)
strategy_runs ──────► recommendations  (run_id 关联)
stocks ◄─────────── recommendations  (stock_code 关联)
```

### 6.2 表结构

**users**
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | |
| username | VARCHAR(64) | UNIQUE NOT NULL | |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**stocks**
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| code | VARCHAR(16) | PK | 如 600000.SH / 000001.SZ |
| name | VARCHAR(64) | NOT NULL | |
| market | VARCHAR(16) | | SH/SZ/BJ |
| status | VARCHAR(16) | DEFAULT 'active' | active/suspended/delisted |
| updated_at | TIMESTAMPTZ | | 最后行情时间 |

**daily_bars**
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| stock_code | VARCHAR(16) | PK(FK→stocks) | 复合主键 |
| date | DATE | PK | 复合主键 |
| open / high / low / close | NUMERIC(12,4) | NOT NULL | |
| volume | NUMERIC(20,0) | NOT NULL | 手 |
| amount | NUMERIC(20,2) | | 成交额 |
| 索引 | | | (stock_code, date) 复合 PK 已覆盖 |

**strategy_runs**
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | run_id |
| strategy | VARCHAR(32) | NOT NULL | turtle / bollinger_mean_reversion |
| run_date | DATE | NOT NULL | |
| status | VARCHAR(16) | DEFAULT 'pending' | pending/running/success/failed |
| started_at / finished_at | TIMESTAMPTZ | | |
| stock_count | INT | | 处理数量 |
| note | TEXT | | 失败清单/错误信息 |
| 索引 | | | (strategy, run_date) |

**recommendations**
| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | |
| run_id | BIGINT | FK→strategy_runs | |
| run_date | DATE | NOT NULL | 冗余便于查询 |
| strategy | VARCHAR(32) | NOT NULL | |
| stock_code | VARCHAR(16) | FK→stocks | |
| signal | VARCHAR(8) | NOT NULL | BUY/HOLD/AVOID |
| score | NUMERIC(6,2) | NOT NULL | 0-100 |
| reason | TEXT | | 中文原因 |
| 索引/约束 | | | UNIQUE(run_date, strategy, stock_code)；INDEX(strategy, run_date, score desc) |

### 6.3 写入策略
- 日线批量写入用 `COPY`/`executemany`，按 `run_date` 分批。
- `daily_bars` 全市场日增量约 5000 行/日，年增量约 125 万行，规模可控；后续可按月分区。

---

## 7. API 设计

Base URL：`/api`。除登录/注册/健康检查外均需 `Authorization: Bearer <token>`。

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | /api/auth/register | 注册（username/password） | 否 |
| POST | /api/auth/login | 登录，返回 access_token + refresh_token | 否 |
| GET | /api/auth/me | 当前用户信息 | 是 |
| GET | /api/strategies | 可用策略元信息 | 是 |
| GET | /api/recommendations | 推荐列表，支持查询参数 | 是 |
| GET | /api/stocks/{code}/bars | 个股日线（二期详情页使用） | 是 |
| GET | /api/health | 健康检查（含 DB 连通性） | 否 |

**GET /api/recommendations 查询参数**
| 参数 | 类型 | 说明 |
|---|---|---|
| strategy | string | turtle / bollinger_mean_reversion，缺省返回全部 |
| date | date | 指定交易日，缺省最新 |
| signal | string | BUY/HOLD/AVOID 过滤 |
| limit / offset | int | 分页，limit 默认 50 |
| order_by | string | score 等，默认 score desc |

**响应示例**
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

### 认证流程
1. 注册 → 密码 bcrypt 哈希入库。
2. 登录 → 校验密码 → 签发 JWT（access 30 分钟 + refresh 7 天，refresh 存 Redis 黑名单/白名单）。
3. 前端带 access token 请求；过期用 refresh token 换取新 access token。

---

## 8. 模块二设计（前端，Web）

### 8.1 技术栈
Next.js 14（App Router）+ TypeScript + Tailwind CSS + Zustand（轻量状态管理）+ SWR（数据请求）。

### 8.2 页面结构（第一期）
```
/                    → 重定向 /login 或 /recommendations
/login               → 登录页（含注册切换）
/recommendations     → 推荐列表页（受保护）
  ├─ 策略 Tab 切换（全部/海龟/布林均值回归）
  ├─ 日期选择器（默认最新交易日）
  ├─ 筛选：信号（BUY/HOLD/AVOID）
  ├─ 排序/分页
  └─ 表格列：代码/名称/策略/评分/信号/原因/日期
```

### 8.3 状态与请求
- Zustand：auth store（token、user、login/logout）。
- SWR：`/api/recommendations`、`/api/strategies` 拉取与缓存。
- API 层统一封装 `fetch` + token 注入 + 401 自动刷新。

### 8.4 图表预留
`components/charts/` 目录预留 ECharts 封装（K 线、成交量、技术指标），二期接入个股详情页，本期不实现。

---

## 9. 每日流水线时序

```
17:00  Cron 触发
  │
  ├─ 1. Redis 获取分布式锁（失败则本轮跳过，另一实例已执行）
  ├─ 2. 创建 strategy_runs 记录（status=pending）
  ├─ 3. 拉取全 A 股代码列表，增量更新 stocks 表
  ├─ 4. 循环拉取日线（akshare → efinance 降级），批量写入 daily_bars
  ├─ 5. 运行策略一（海龟）→ 写 recommendations
  ├─ 6. 运行策略二（布林带均值回归）→ 写 recommendations
  ├─ 7. 更新 strategy_runs（status=success，记录数量/失败清单）
  └─ 8. 释放锁
```

失败处理：单股拉取失败不阻断（记录日志）；策略计算异常记录到 note；重试机制（同任务最多重跑 2 次）。

---

## 10. 部署设计

### 10.1 服务拓扑（docker-compose）
```
┌──────────────────────────────────────────────┐
│  nginx:80  (反向代理 + 静态资源)                │
│    /      → web (Next.js standalone)          │
│    /api   → backend (FastAPI uvicorn)         │
│  backend  (uvicorn 服务)                       │
│  web      (Next.js standalone 静态服务)         │
│  db       (postgres:16-alpine)                │
│  redis    (redis:7-alpine)                    │
└──────────────────────────────────────────────┘
```

### 10.2 环境变量清单
| 变量 | 说明 |
|---|---|
| DATABASE_URL | postgresql+psycopg://... |
| REDIS_URL | redis://redis:6379/0 |
| JWT_SECRET | JWT 签名密钥 |
| JWT_ACCESS_TTL / JWT_REFRESH_TTL | 令牌有效期 |
| SCHEDULE_ENABLED | 是否启用 APScheduler（worker 与 API 分离时控制） |
| TZ | Asia/Shanghai |

### 10.3 启动
- `docker compose up -d` 一键拉起全部服务。
- `docker compose run backend alembic upgrade head` 初始化数据库。
- 数据卷持久化 PostgreSQL 与 Redis。

---

## 11. 项目目录结构

```
opencode_workspace/
├── docs/
│   └── design.md                    # 本文档
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml / requirements.txt
│   ├── alembic/                     # 数据库迁移
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口
│   │   ├── core/                    # 配置、安全、日志
│   │   ├── api/                     # 路由（auth/recommendations/strategies/health）
│   │   ├── models/                  # SQLAlchemy 模型
│   │   ├── schemas/                 # Pydantic 模型
│   │   ├── services/                # 业务逻辑
│   │   │   ├── data_fetcher.py      # akshare/efinance 获取+降级
│   │   │   ├── scheduler.py         # APScheduler + Redis 锁
│   │   │   └── pipeline.py          # do_heavy_computation 入口
│   │   └── strategies/              # 策略引擎
│   │       ├── base.py              # 统一接口 + 注册表
│   │       ├── turtle.py            # 海龟
│   │       ├── bollinger_reversion.py  # 布林带均值回归
│   │       └── config.py            # 策略参数外置
│   ├── tests/
│   └── requirements.txt
├── web-app/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.mjs
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/page.tsx
│   │   │   ├── recommendations/page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/              # 表格、筛选、图表(预留)
│   │   ├── stores/                  # Zustand
│   │   ├── lib/                     # api client、types
│   │   └── types/
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

---

## 12. 里程碑计划

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| M1 后端跑通 | 数据层 + 策略引擎 + 调度 + API | 手动触发流水线，全市场数据入库，双策略产出推荐，`/api/recommendations` 返回 JSON |
| M2 前端联调 | 登录 + 推荐列表页 | 登录后展示推荐列表，筛选/排序可用 |
| M3 部署 | Docker Compose + Nginx | 一键启动，Nginx 正确路由，每日定时任务自动运行 |
| M4（二期） | 个股详情 K 线、自选股、图表增强 | 未排期 |

---

## 13. 风险与待定事项

| 事项 | 说明 |
|---|---|
| akshare 接口稳定性 | 接口偶发变动/限流，需监控与降级验证 |
| 全市场拉取时长 | 10-30 分钟，需在 17:00 后留有足够窗口；接口速率受限时动态限速 |
| ST/退市股 | 需持续维护股票状态过滤 |
| 策略有效性 | 策略参数基于历史经验设定，需后续引入回测验证与参数调优（不在本期范围） |
| Celery 迁移 | 预留演进路径，初期不过度设计（见 §5.3） |
