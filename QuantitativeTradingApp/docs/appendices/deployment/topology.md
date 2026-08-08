# 附录 · 部署 · 服务拓扑

> 主文档：../../design.md · 版本随 v0.5 同步

## docker-compose 拓扑

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

## 路由职责

- `nginx` 统一入口：`/` 静态资源走 web，`/api` 反代到 backend。
- Nginx 需透传 `X-Forwarded-For`（限流 IP 识别依赖，见 [限流](../api/rate-limiting.md)）。
- 数据卷持久化 PostgreSQL 与 Redis。

[← 返回 design.md](../../design.md)
