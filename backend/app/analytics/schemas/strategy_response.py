"""
策略API响应模式
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class StrategyResponse(BaseModel):
    """策略响应模型"""

    id: int
    user_id: int
    name: str
    description: str | None = None
    definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BacktestResultResponse(BaseModel):
    """回测结果响应模型"""

    id: int
    strategy_id: int
    user_id: int
    symbol: str
    interval: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyListResponse(BaseModel):
    """策略列表响应"""

    strategies: list[StrategyResponse]


class BacktestResultListResponse(BaseModel):
    """回测结果列表响应"""

    results: list[BacktestResultResponse]


class CreateStrategyResponse(BaseModel):
    """创建策略响应"""

    id: int
    message: str


class UpdateStrategyResponse(BaseModel):
    """更新策略响应"""

    message: str


class DeleteStrategyResponse(BaseModel):
    """删除策略响应"""

    message: str
