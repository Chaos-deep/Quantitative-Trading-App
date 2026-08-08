# 附录 · API · 速率限制

> 主文档：../../design.md · 版本随 v0.5 同步

## 规则

面向公开互联网访问，必须防范暴力破解与爬虫。引入 `slowapi`（基于 Redis 计数器）：

| 端点 | 限制 | 目的 |
|---|---|---|
| POST /api/auth/login | 每 IP 每分钟 5 次 | 防撞库 |
| GET /api/recommendations/global | 每用户每分钟 60 次 | 防爬虫全量拉取 |
| GET /api/recommendations/personal | 每用户每分钟 60 次 | 防爬虫全量拉取 |

- 限流触发返回 **HTTP 429**（含 `Retry-After` 响应头，值为窗口重置前的剩余秒数）。

## 实现注意（与代码同步）

- 依赖 `slowapi`。限流按 **IP**（登录）或 **用户**（推荐接口）为 key：
  - 登录：`ip:{真实客户端IP}`。
  - 推荐：`user:{user_id}`；解析不到 token 时降级为 IP key。
- **装饰器顺序**：`@router.get/post(...)` 必须在外层，`@limiter.limit(...)` 紧贴函数体；顺序颠倒会导致路由注册失败。
- `slowapi` 的响应头注入（`headers_enabled=True`）要求端点返回 `starlette.Response`，与本项目返回 Pydantic 模型/dict 的写法不兼容，故**关闭该选项**；`Retry-After` 在 429 异常处理器中用 `limiter.get_window_stats` 手动计算。
- 可通过环境变量 `RATE_LIMIT_ENABLED=false` 临时关闭（测试/压测），`RATE_LIMIT_STORAGE` 可覆盖计数存储（如 `memory://`）。

## IP 识别（XFF 信任）

- 限流按真实客户端 IP 计。
- Nginx 需透传 `X-Forwarded-For`。
- 应用层**信任该头（仅信任来自 Nginx 的来源）**，否则 Docker 拓扑下所有请求共享 Nginx 一个 IP、限流失效。

## 配置注意

- 错误配置将导致限流失效（都按 Nginx IP 计）或误伤（直接信任客户端伪造的 XFF）。
- 依赖 Nginx 反向代理层正确设置，见 [部署拓扑](../deployment/topology.md)。

[← 返回 design.md](../../design.md)
