# 附录 · API · 认证（JWT 令牌模型）

> 主文档：../../../design.md · 版本随 v0.5 同步

## 令牌模型

- **Access Token**：有效期 30 分钟，请求鉴权用。
- **Refresh Token**：有效期 7 天，携带唯一 `jti`（JWT ID），用于换取新令牌。

## 严格黑名单方案

核心思路：**登录时不存任何会话状态**，仅在令牌被吊销时写入黑名单，命中即拒绝。

- 黑名单为增量数据，仅含被吊销的 token，成本极低。
- 支持服务端主动吊销。

## 关键语义（必须遵守）

| 动作 | 语义 |
|---|---|
| 登出 | 将 refresh_token 的 `jti` **写入**黑名单（不是删除，黑名单里本来就什么都没有） |
| 刷新命中黑名单 | **拒绝**——该 refresh 已吊销 |
| 刷新放行 | 签发新 access + 新 refresh（新 `jti`），**同时将旧 `jti` 写入黑名单**（防重放） |

> 严格黑名单与“删除即视为已登出”的宽松方案相反：宽松方案中刷新旧 token 等于重新登录，安全语义被破坏。本项目采用严格方案，登出后的 refresh 再刷新**必须失败**。

## 存储

- Redis 键：`refresh_token:{jti}`，Value 为 User ID。
- TTL = 该 token 剩余有效期（≤7 天），到期自动淘汰，无需手动清理。

## 全设备踢出（可选）

- JWT payload 增加 `ver`（token_version）声明。
- 服务端维护 `user:{id}:token_version` 递增计数。
- 验签时 `ver` 不匹配即拒绝，一次性作废该用户全部已签发 token。
- 用于密码修改 / 账号异常等场景。

## 刷新严格检查顺序（必须按序执行）

`POST /api/auth/refresh` 内部必须严格按以下顺序执行，**顺序不可颠倒**（`ver` 的校验不能漏检）：

1. **验签**（签名无效 → 401）。
2. **解码提取** `jti` 与 `ver`。
3. **查 Redis 黑名单** `refresh_token:{jti}` → **存在即拒绝**（该 refresh 已吊销）。
4. **查 `user:{id}:token_version` 是否等于 `ver`** → 不等则**立即拒绝**（返回 401，该用户 token 已被全设备作废）。
5. **全部通过** → 签发新 access + 新 refresh（新 `jti`），并将**旧 `jti` 写入黑名单**（防重放）。

## 完整流程

1. 注册 → 密码 bcrypt 哈希入库。
2. 登录 → 校验密码 → 签发 JWT（access 30 分钟 + refresh 7 天，refresh 携带唯一 `jti`）。
3. 刷新 → 严格按「刷新严格检查顺序」五步执行（见上节）。
4. 登出 → 提取 refresh 的 `jti` 写入黑名单，该设备 Refresh Token 立即失效；Access Token 因 30 分钟自然过期而失效。

[← 返回 design.md](../../../design.md)
