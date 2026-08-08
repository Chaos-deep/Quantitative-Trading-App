# 附录 · 策略参考 · 海龟交易法则（核心代码实现）

> 主文档：../../design.md · 版本随 v0.5 同步

## 十二、核心代码实现参考

```python
import pandas as pd
import numpy as np

# 1. 计算N值（20日ATR）
def calc_atr(high, low, close, period=20):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

# 2. 计算唐奇安通道
def calc_donchian(high, low, period):
    upper = high.rolling(period).max()
    lower = low.rolling(period).min()
    return upper, lower

# 3. 计算单位大小（A股简化版）
def calc_unit(equity, atr, risk_pct=0.01):
    return int(equity * risk_pct / atr / 100) * 100  # 100股为单位

# 4. 止损价计算（逐笔法）
def calc_stop_price(entry_price, atr, units_held):
    # 第units_held个单位的止损价
    return entry_price - 2 * atr + (units_held - 1) * 0.5 * atr
```

[← 返回 design.md](../../design.md)
