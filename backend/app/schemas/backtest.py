from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date
from enum import Enum

class UpperBoundStrategy(str, Enum):
    HOLD = "hold"
    SELL_ALL = "sell_all"

class LowerBoundStrategy(str, Enum):
    HOLD = "hold"
    SELL_ALL = "sell_all"

class GridStrategyConfig(BaseModel):
    """
    Configuration for a grid trading backtest.
    Sent from the frontend to the backend.
    """
    stock_code: str
    start_date: date
    end_date: date
    upper_price: float
    lower_price: float
    grid_count: int
    total_investment: float
    initial_quantity: Optional[int] = Field(0, description="Optional: Number of shares held at the start of the backtest.")
    initial_per_share_cost: Optional[float] = Field(0.0, description="Optional: Per-share cost of the initial holdings.")
    on_exceed_upper: Optional[UpperBoundStrategy] = Field(UpperBoundStrategy.HOLD, description="Strategy when price exceeds upper bound.")
    on_fall_below_lower: Optional[LowerBoundStrategy] = Field(LowerBoundStrategy.HOLD, description="Strategy when price falls below lower bound.")
    
    # Transaction Costs
    commission_rate: Optional[float] = Field(0.0003, description="Commission rate per transaction.")
    stamp_duty_rate: Optional[float] = Field(0.001, description="Stamp duty rate, applied on sells only.")
    min_commission: Optional[float] = Field(5.0, description="Minimum commission fee per transaction.")

class Transaction(BaseModel):
    """
    Represents a single trade executed during the backtest.
    """
    trade_date: date
    trade_type: str  # "buy" or "sell"
    price: float
    quantity: int
    pnl: Optional[float] = Field(None, description="Profit and Loss for this specific trade (realized on sell)")

class ChartDataPoint(BaseModel):
    """
    Represents a single data point for the portfolio value chart.
    """
    date: date
    portfolio_value: float
    benchmark_value: float

class KLineDataPoint(BaseModel):
    """
    Represents a single OHLCV data point for the K-line chart.
    """
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    vol: int

class BacktestResult(BaseModel):
    """
    The detailed results of a backtest, structured for frontend display.
    """
    # 1. Core KPI Metrics
    total_pnl: float = Field(..., description="Total Profit and Loss")
    total_return_rate: float = Field(..., description="Total return rate as a percentage of initial investment")
    annualized_return_rate: float = Field(..., description="Annualized rate of return")
    max_drawdown: float = Field(..., description="Maximum drawdown experienced during the backtest")
    win_rate: float = Field(..., description="Percentage of profitable trades out of all sell trades")
    trade_count: int = Field(..., description="Total number of trades (buys and sells)")

    # 2. Data for Charts and Tables
    chart_data: List[ChartDataPoint] = Field(..., description="Data for plotting portfolio and benchmark value over time")
    kline_data: List[KLineDataPoint] = Field(..., description="OHLCV data for plotting the K-line chart")
    transaction_log: List[Transaction] = Field(..., description="A detailed log of all trades executed")
    
    # 3. Informational data
    strategy_config: GridStrategyConfig = Field(..., description="The configuration used for this backtest")
    market_type: str = Field(..., description="The market type of the stock (e.g., 'A_share', 'US_stock')")

    # 4. Final Holdings
    final_holding_quantity: int = Field(..., description="Number of shares still held at the end of the backtest.")
    average_holding_cost: float = Field(..., description="The average cost per share of the final holdings.")
