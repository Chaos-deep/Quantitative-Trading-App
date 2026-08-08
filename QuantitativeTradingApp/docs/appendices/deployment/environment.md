# 附录 · 部署 · 环境变量

> 主文档：../../design.md · 版本随 v0.4 同步

| 变量 | 说明 |
|---|---|
| DATABASE_URL | postgresql+psycopg://... |
| REDIS_URL | redis://redis:6379/0 |
| JWT_SECRET | JWT 签名密钥 |
| JWT_ACCESS_TTL / JWT_REFRESH_TTL | 令牌有效期 |
| SCHEDULE_ENABLED | 是否启用 APScheduler（worker 与 API 分离时控制） |
| LOG_DIR | 日志目录（容器内挂载点，默认 /var/log/app） |
| LOG_LEVEL | 日志级别（默认 INFO） |
| TZ | Asia/Shanghai |

## 说明

- **JWT_SECRET 必须通过 Secret 注入**，禁止写入镜像或代码仓库。
- `TZ=Asia/Shanghai` 贯穿全部服务与调度时区判断。
- `SCHEDULE_ENABLED`：worker 与 API 分离部署时，仅在调度实例开启。

[← 返回 design.md](../../design.md)
