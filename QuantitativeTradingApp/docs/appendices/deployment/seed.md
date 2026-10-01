# 附录 · 部署 · 种子脚本

> 主文档：../../design.md · 版本随 v0.5 同步

`backend/seed.py`：写入开发/演示用种子数据。

## 内容

- **示例用户**：`admin`、`alice`、`bob`，含各自持仓（user_positions）与偏好（user_preferences，risk_level + total_capital），便于验证模块三个性化建议。
- 脚本末尾补充 **SEED_STOCKS**（若库中不存在），供搜索/持仓录入演示。

## 口令注入（不硬编码）

种子脚本不包含任何明文口令，按以下顺序解析：

1. 读取环境变量 `SEED_<用户名大写>_PASSWORD`（如 `SEED_ADMIN_PASSWORD`）；
2. 未设置时，脚本**随机生成**强口令并仅打印一次，请立即保存。

示例：

```bash
# 显式指定
export SEED_ADMIN_PASSWORD='<强口令>'
python seed.py

# 不指定：随机生成并打印一次
python seed.py
# 创建用户: admin  随机口令: xxxxxxxxxxxxxxxx  （仅显示一次，请立即保存）
```

## 约束

- 种子脚本需幂等（重复执行不产生重复/脏数据）；已存在的用户会跳过，不会重置口令。
- 仅用于开发与演示环境，生产环境不执行。
- 真实环境凭据一律通过环境变量/Secret 注入，禁止写入代码或文档。

[← 返回 design.md](../../design.md)
