# 附录 · 部署 · 环境变量

> 主文档：../../design.md · 版本随 v0.5 同步

| 变量 | 说明 | 默认值 |
|---|---|---|
| APP_NAME | 应用名 | A股量化选股系统 |
| API_PREFIX | 路由前缀 | /api |
| DEBUG | 调试模式 | false |
| DATABASE_URL | postgresql+psycopg://... | postgresql+psycopg://quant:quant@localhost:5432/quant |
| REDIS_URL | redis://... | redis://localhost:6379/0 |
| JWT_SECRET | JWT 签名密钥 | CHANGE_ME_IN_PRODUCTION |
| JWT_ALGORITHM | JWT 签名算法 | HS256 |
| JWT_ACCESS_TTL | access token 有效期（秒） | 1800 |
| JWT_REFRESH_TTL | refresh token 有效期（秒） | 604800 |
| TZ | 应用时区（调度/日期统一） | Asia/Shanghai |
| SCHEDULE_ENABLED | 是否启用 APScheduler（worker 与 API 分离时控制） | true |
| SCHEDULE_CRON_HOUR / SCHEDULE_CRON_MINUTE | 每日流水线触发时间（Asia/Shanghai） | 17 / 0 |
| LOCK_TTL | Redis 分布式锁 TTL（秒） | 7200 |
| RATE_LIMIT_ENABLED | 关闭后 slowapi 直接放行（测试/压测环境用） | true |
| RATE_LIMIT_STORAGE | 限流计数存储；不填则用 REDIS_URL | 空 |
| TRUST_XFF | 是否信任 Nginx 透传的 X-Forwarded-For | true |
| CORS_ORIGINS | 逗号分隔的允许来源（开发默认全放行） | * |
| LOG_DIR | 日志目录（容器内挂载点） | /var/log/app |
| LOG_LEVEL | 日志级别 | INFO |

## 说明

- **JWT_SECRET 必须通过 Secret 注入**，禁止写入镜像或代码仓库。
- `TZ=Asia/Shanghai` 贯穿全部服务与调度时区判断。
- `SCHEDULE_ENABLED`：worker 与 API 分离部署时，仅在调度实例开启。
- 限流相关配置见 [限流附录](../api/rate-limiting.md)。

[← 返回 design.md](../../design.md)
