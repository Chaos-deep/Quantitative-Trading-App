"""策略包：导入即完成注册（STRATEGY_REGISTRY 填充 turtle / bollinger_mean_reversion）。"""

from app.strategies.base import STRATEGY_REGISTRY, BaseStrategy, Recommendation
from app.strategies.bollinger_reversion import BollingerMeanReversionStrategy
from app.strategies.turtle import TurtleStrategy

__all__ = [
    "STRATEGY_REGISTRY",
    "BaseStrategy",
    "Recommendation",
    "TurtleStrategy",
    "BollingerMeanReversionStrategy",
]
