# 附录 · API · 认证端点

> 主文档：../../../design.md · 版本随 v0.5 同步

Base URL：`/api`。除登录/注册/健康检查外均需 `Authorization: Bearer <token>`。

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | /api/auth/register | 注册（username/password） | 否 |
| POST | /api/auth/login | 登录，返回 access_token + refresh_token | 否 |
| POST | /api/auth/logout | 登出，将 refresh_token 的 jti 写入黑名单 | 是 |
| POST | /api/auth/refresh | 用 refresh_token 换新 access（验签 → 查黑名单 → 放行并轮换、旧 jti 入黑名单） | 否 |
| GET | /api/auth/me | 当前用户信息 | 是 |

## 端点细节

### POST /api/auth/register

请求体：
```json
{ "username": "alice", "password": "secret123" }
```

- 密码 bcrypt 哈希后入库。
- 返回：`201` + 用户信息（不含密码哈希）。

### POST /api/auth/login

请求体：
```json
{ "username": "alice", "password": "secret123" }
```

返回：
```json
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
```

- 校验失败返回 `401`。
- 限流：每 IP 每分钟 5 次（见 [限流](../rate-limiting.md)）。

### POST /api/auth/logout

请求体：
```json
{ "refresh_token": "..." }
```

- 服务端提取 `jti` 写入 Redis 黑名单 `refresh_token:{jti}`，Value=User ID，TTL=剩余有效期。
- 返回 `204`。幂等：重复提交同一 token 无害。

### POST /api/auth/refresh

请求体：
```json
{ "refresh_token": "..." }
```

流程：验签 → 查黑名单（命中即拒绝，`401`）→ 签发新 access + 新 refresh → 旧 `jti` 写入黑名单。

### GET /api/auth/me

返回当前用户信息（username、created_at 等），`Authorization` 缺失或失效返回 `401`。

[← 返回 design.md](../../../design.md)
