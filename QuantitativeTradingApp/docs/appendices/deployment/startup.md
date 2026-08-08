# 附录 · 部署 · 启动流程

> 主文档：../../design.md · 版本随 v0.4 同步

```bash
docker compose up -d                                   # 一键拉起全部服务
docker compose run backend alembic upgrade head        # 初始化数据库（Alembic 迁移）
docker compose run backend python seed.py              # 写入种子数据（可选）
```

## 说明

- 数据卷持久化 PostgreSQL 与 Redis，重启不丢数据。
- 数据库结构变更统一走 Alembic，禁止手写变更 SQL。
- 种子脚本内容见 [seed](seed.md)。

[← 返回 design.md](../../design.md)
