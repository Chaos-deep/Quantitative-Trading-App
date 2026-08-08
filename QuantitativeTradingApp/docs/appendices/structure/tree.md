# 附录 · 目录结构

> 主文档：../design.md · 版本随 v0.4 同步

## 项目目录树

```
opencode_workspace/
├── docs/
│   ├── design.md                    # 本文档（主文档）
│   └── appendices/                  # 分层附录
│       ├── database/                # 数据库（表结构 / DDL / 写入策略）
│       ├── api/                     # API 规范（认证 / 推荐 / 限流）
│       ├── pipeline/                # 调度流水线（时序 / 锁 / 失败处理）
│       ├── frontend/                # 前端（页面 / 状态 / 图表预留）
│       ├── deployment/              # 部署（拓扑 / 环境变量 / 启动 / seed / 可观测性）
│       ├── structure/               # 本附录
│       ├── risks/                   # 风险登记
│       └── turtle/                  # 策略参考（海龟交易法则）
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml / requirements.txt
│   ├── alembic/
│   │   └── versions/              # 数据库迁移文件
│   ├── seed.py                    # 种子脚本（admin 测试用户 + 示例用户/持仓/偏好）
│   ├── app/
│   │   ├── main.py                # FastAPI 入口
│   │   ├── core/                  # config(Pydantic Settings)/security/redis_client/dependencies（限流+XFF）
│   │   ├── api/                   # 路由（auth/recommendations/stocks/positions/preferences/health）
│   │   ├── models/                # SQLAlchemy 模型（含 user_positions 等）
│   │   ├── schemas/               # Pydantic 模型
│   │   ├── services/              # 业务逻辑
│   │   │   ├── market_data.py     # 模块一：适配器模式（akshare/efinance 获取+降级）
│   │   │   ├── strategy_engine.py # 模块二：海龟/布林带（逐股流式）
│   │   │   ├── personal_advisor.py# 模块三：个性化投顾（内存批量计算 + upsert）
│   │   │   ├── scheduler.py       # APScheduler + Lua 锁 + 交易日判断
│   │   │   └── pipeline.py        # run_pipeline_core 入口
│   │   ├── strategies/            # 策略引擎（插件注册 STRATEGY_REGISTRY）
│   │   │   ├── base.py            # 统一接口 + 注册表
│   │   │   ├── turtle.py          # 海龟
│   │   │   ├── bollinger_reversion.py  # 布林带均值回归
│   │   │   └── config.py          # 策略参数外置
│   │   └── utils/                 # 日志、日期工具
│   ├── tests/
│   └── requirements.txt
├── web-app/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.mjs
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/login/page.tsx
│   │   │   ├── (protected)/recommendations/page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/              # 表格、筛选器、信号标签、持仓/偏好表单、图表预留
│   │   ├── stores/                  # Zustand（auth store）
│   │   ├── lib/                     # api client（401 拦截 + refreshAttempted）
│   │   └── types/
│   └── public/
├── nginx/
│   └── nginx.conf                    # 必须传递 X-Forwarded-For / X-Request-ID
├── docker-compose.yml
└── .env.example
```

[← 返回 design.md](../../design.md)
