"""策略统一接口与注册表（插件式）。

每个策略实现 run(bars: pd.DataFrame) -> Recommendation | None：
- bars 为单只股票的日线 DataFrame（按日期升序），含 date/open/high/low/close/volume/amount。
- 返回 None 表示过滤跳过（如上市不足、低波动、ST 等）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

BUY = "BUY"
HOLD = "HOLD"
AVOID = "AVOID"

SIGNALS = (BUY, HOLD, AVOID)


@dataclass
class Recommendation:
    strategy: str
    run_date: date
    stock_code: str
    signal: str
    score: float  # 0-100
    close: float
    reason: str = field(default="")


class BaseStrategy(ABC):
    """统一策略接口。子类定义 name/display_name/description 即自动注册。"""

    name: str = ""
    display_name: str = ""
    description: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.name:
            STRATEGY_REGISTRY[cls.name] = cls

    @abstractmethod
    def run(self, bars: pd.DataFrame) -> Recommendation | None:
        """对单只股票日线运行策略，返回推荐或 None（过滤跳过）。"""


STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {}


def register_strategy(cls: type[BaseStrategy]) -> type[BaseStrategy]:
    """显式注册装饰器（__init_subclass__ 已自动注册，此函数留作工具）。"""
    STRATEGY_REGISTRY[cls.name] = cls
    return cls


def get_strategy(name: str) -> BaseStrategy | None:
    cls = STRATEGY_REGISTRY.get(name)
    return cls() if cls else None


def all_strategy_meta() -> list[dict]:
    return [
        {
            "name": cls.name,
            "display_name": cls.display_name,
            "description": cls.description,
        }
        for cls in STRATEGY_REGISTRY.values()
    ]
