# 附录 · 前端 · 状态与请求

> 主文档：../../design.md · 版本随 v0.4 同步

## 状态管理

- **Zustand**：auth store（access/refresh token、user、login/logout/refresh 方法）。
- **SWR**：`/api/recommendations/global`、`/api/recommendations/personal`、`/api/strategies` 拉取与缓存。

## API 层（lib/api client）

统一封装 `fetch` + token 注入 + 401 自动刷新。

### 防死循环：`refreshAttempted` 标志（必须遵守）

拦截器内置 `refreshAttempted` 标志：

1. 请求携带 access token 发出。
2. 返回 401 → 若 `refreshAttempted === false`，置为 true，用 refresh token 调用刷新接口，成功后重放原请求。
3. 若刷新接口也返回 401（refresh 过期或已吊销）→ **直接清空 auth store 并 `window.location.href = '/login'`**。

> 禁止无限重试刷新。若仅凭"请求再失败就再刷新"的实现，同一并发请求组会导致刷新风暴与死循环。

## 登出

调用 `POST /api/auth/logout` 吊销 refresh token（服务端写黑名单），成功后清空本地状态。

[← 返回 design.md](../../design.md)
