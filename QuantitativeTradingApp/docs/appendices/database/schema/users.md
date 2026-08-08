# 附录 · 数据库 · users 表

> 主文档：../../../design.md · 版本随 v0.5 同步

## 用途

用户认证信息存储。

## 表结构

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PK | |
| username | VARCHAR(64) | UNIQUE NOT NULL | |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

## 说明

- 密码一律 bcrypt 哈希后入库，明文不出现在任何持久化层。
- 登录成功后不写任何会话状态（JWT 严格黑名单方案，见 [API 认证](../../api/auth/jwt.md)）。

[← 返回 design.md](../../../design.md)
