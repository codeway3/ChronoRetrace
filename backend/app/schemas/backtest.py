from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator

# --- Enums and Basic Types ---


class UpperBoundStrategy(str, Enum):
    HOLD = "hold"
    SELL_ALL = "sell_all"


class LowerBoundStrategy(str, Enum):
    HOLD = "hold"
    SELL_ALL = "sell_all"


# A type to represent a value that can be a single float or a range for optimization
# Example: 5.0 or [5.0, 10.0, 1.0] for start, stop, step
RangeValue = float | list[float]

# --- Strategy Configuration Models ---


class GridStrategyConfig(BaseModel):
    """
    Configuration for a SINGLE grid trading backtest.
    """

    stock_code: str
    start_date: date
    end_date: date
    upper_price: float
    lower_price: float
    grid_count: int
    total_investment: float

    initial_quantity: int = 0
    initial_per_share_cost: float = 0.0
    on_exceed_upper: UpperBoundStrategy = UpperBoundStrategy.HOLD
    on_fall_below_lower: LowerBoundStrategy = LowerBoundStrategy.HOLD
    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    min_commission: float = 5.0

    @field_validator("end_date")
    @classmethod
    def check_date_range(cls, v, info):
        if info.data and "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("End date must be after or equal to start date")
        return v


class GridStrategyOptimizeConfig(BaseModel):
    """
    Configuration for a grid trading PARAMETER OPTIMIZATION.
    Allows ranges for key parameters.
    """

    stock_code: str
    start_date: date
    end_date: date

    # Parameters that can be optimized are defined as ranges
    upper_price: RangeValue
    lower_price: RangeValue
    grid_count: int | list[int]  # Grid count must be integer

    total_investment: float
    initial_quantity: int = 0
    initial_per_share_cost: float = 0.0
    on_exceed_upper: UpperBoundStrategy = UpperBoundStrategy.HOLD
    on_fall_below_lower: LowerBoundStrategy = LowerBoundStrategy.HOLD
    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    min_commission: float = 5.0

    @field_validator("upper_price", "lower_price", "grid_count")
    @classmethod
    def check_range_format(cls, v):
        if isinstance(v, list):
            if len(v) != 3:
                raise ValueError(
                    "Range list must contain exactly 3 elements: [start, stop, step]"
                )
            if v[2] <= 0:
                raise ValueError("Step value in a range must be positive")
        return v

    @field_validator("end_date")
    @classmethod
    def check_date_range(cls, v, info):
        if info.data and "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("End date must be after or equal to start date")
        return v


# --- Result Models ---


class Transaction(BaseModel):
    trade_date: date
    trade_type: str
    price: float
    quantity: int
    pnl: float | None = None


class ChartDataPoint(BaseModel):
    date: date
    portfolio_value: float
    benchmark_value: float


class KLineDataPoint(BaseModel):
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    vol: int


class BacktestResult(BaseModel):
    """
    Represents the detailed results of a SINGLE backtest run.
    """

    total_pnl: float
    total_return_rate: float
    annualized_return_rate: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trade_count: int

    chart_data: list[ChartDataPoint]
    kline_data: list[KLineDataPoint]
    transaction_log: list[Transaction]

    strategy_config: GridStrategyConfig  # The exact config used for this run
    market_type: str
    final_holding_quantity: int
    average_holding_cost: float


class OptimizationResultItem(BaseModel):
    """
    A summary of a single run within a larger optimization task.
    """

    parameters: dict[str, Any]
    annualized_return_rate: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trade_count: int


class BacktestOptimizationResponse(BaseModel):
    """
    The final response for a parameter optimization request.
    """

    optimization_results: list[OptimizationResultItem]
    best_result: OptimizationResultItem
