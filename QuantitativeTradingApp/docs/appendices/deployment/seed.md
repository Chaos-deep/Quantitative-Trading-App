# 附录 · 部署 · 种子脚本

> 主文档：../../design.md · 版本随 v0.5 同步

`backend/seed.py`：写入开发/演示用种子数据。

## 内容

- **admin 测试用户**：`admin` / `admin123`，密码 bcrypt 哈希入库。
- **2~3 个示例用户**：`alice` / `alice123`、`bob` / `bob123`，含各自持仓（user_positions）与偏好（user_preferences，risk_level + total_capital），便于验证模块三个性化建议。
- 脚本末尾补充 **SEED_STOCKS**（若库中不存在），供搜索/持仓录入演示。

## 约束

- 种子脚本需幂等（重复执行不产生重复/脏数据）。
- 仅用于开发与演示环境，生产环境不执行。
- 密码明文仅存在于脚本内示例，真实环境凭据一律通过环境变量/Secret 注入。

[← 返回 design.md](../../design.md)
