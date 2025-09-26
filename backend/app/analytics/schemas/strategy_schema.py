"""
策略定义模式 - 定义策略JSON结构
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ConditionType(str, Enum):
    """条件类型枚举"""

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    PRICE = "price"


class ActionType(str, Enum):
    """动作类型枚举"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Condition(BaseModel):
    """策略条件"""

    type: ConditionType
    indicator: str = Field(..., description="技术指标名称，如'macd', 'rsi'等")
    operator: str = Field(
        ..., description="比较运算符：'>', '<', '>=', '<=', '==', '!='"
    )
    value: float = Field(..., description="比较值")
    lookback_period: int | None = Field(14, description="回溯周期")


class Action(BaseModel):
    """策略动作"""

    type: ActionType
    condition_id: int = Field(..., description="触发此动作的条件ID")
    position_size: float = Field(1.0, ge=0.0, le=1.0, description="仓位比例(0-1)")
    stop_loss: float | None = Field(None, description="止损比例")
    take_profit: float | None = Field(None, description="止盈比例")


class StrategyDefinition(BaseModel):
    """策略定义"""

    version: str = Field("1.0", description="策略版本")
    description: str | None = Field(None, description="策略描述")

    # 策略参数
    symbols: list[str] = Field(..., min_length=1, description="交易标的列表")
    interval: str = Field("1d", description="时间间隔：1d, 1h, 30m, 15m, 5m, 1m")
    initial_capital: float = Field(100000.0, gt=0, description="初始资金")

    # 策略逻辑
    conditions: list[Condition] = Field(..., min_length=1, description="条件列表")
    actions: list[Action] = Field(..., min_length=1, description="动作列表")

    # 风险管理
    max_position_size: float = Field(
        0.1, ge=0.0, le=1.0, description="最大单笔仓位比例"
    )
    max_drawdown: float | None = Field(0.2, ge=0.0, le=1.0, description="最大回撤限制")

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v):
        valid_intervals = ["1d", "1h", "30m", "15m", "5m", "1m"]
        if v not in valid_intervals:
            raise ValueError(f"间隔必须是以下之一: {valid_intervals}")
        return v

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, v, info):
        if hasattr(info, "data") and "conditions" in info.data:
            condition_ids = [cond for cond in range(len(info.data["conditions"]))]
            for action in v:
                if action.condition_id not in condition_ids:
                    raise ValueError(f"动作引用了不存在的条件ID: {action.condition_id}")
        return v


# 示例策略定义
example_strategy = StrategyDefinition(
    version="1.0",
    description="简单的双均线策略",
    symbols=["AAPL", "MSFT"],
    interval="1d",
    initial_capital=100000,
    conditions=[
        Condition(
            type=ConditionType.TECHNICAL,
            indicator="sma",
            operator=">",
            value=50,
            lookback_period=20,
        ),
        Condition(
            type=ConditionType.TECHNICAL,
            indicator="sma",
            operator="<",
            value=20,
            lookback_period=10,
        ),
    ],
    actions=[
        Action(
            type=ActionType.BUY,
            condition_id=0,
            position_size=0.5,
            stop_loss=0.05,
            take_profit=0.1,
        ),
        Action(type=ActionType.SELL, condition_id=1, position_size=1.0),
    ],
    max_position_size=0.2,
    max_drawdown=0.15,
)
