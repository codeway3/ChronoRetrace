"""
回测引擎核心模块
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TradeAction(Enum):
    """交易动作枚举"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Trade:
    """交易记录类"""

    def __init__(
        self,
        symbol: str,
        action: TradeAction,
        quantity: float,
        price: float,
        timestamp: datetime,
        commission: float = 0.0,
    ):
        self.symbol = symbol
        self.action = action
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp
        self.commission = commission
        self.value = quantity * price

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "commission": self.commission,
            "value": self.value,
        }


class BacktestEngine:
    """回测引擎核心类"""

    def __init__(
        self, initial_capital: float = 100000.0, commission_rate: float = 0.001
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.reset()

    def reset(self):
        """重置回测状态"""
        self.cash = self.initial_capital
        self.positions: dict[str, float] = {}  # 持仓数量
        self.trades: list[Trade] = []  # 交易记录
        self.equity_curve: list[dict[str, Any]] = []  # 权益曲线
        self.current_date = None
        self.portfolio_value = self.initial_capital

    def run_backtest(
        self, data: pd.DataFrame, strategy_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """执行回测"""
        self.reset()
        try:
            # 预处理数据
            data = self._preprocess_data(data)
            # 执行回测
            for i, (timestamp, row) in enumerate(data.iterrows()):
                self.current_date = timestamp
                # 更新持仓市值
                self._update_portfolio_value(row)
                # 执行策略逻辑
                signals = self._generate_signals(
                    row, strategy_definition, data.iloc[: i + 1]
                )
                # 执行交易
                self._execute_trades(signals, row)
                # 记录权益曲线
                self._record_equity_curve()
            # 计算性能指标
            performance = self._calculate_performance_metrics()
            return {
                "performance_metrics": performance,
                "trades": [trade.to_dict() for trade in self.trades],
                "equity_curve": self.equity_curve,
                "final_portfolio_value": self.portfolio_value,
                "final_cash": self.cash,
                "final_positions": self.positions,
            }
        except Exception as e:
            logger.error(f"回测执行失败: {e}")
            raise

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理数据"""
        # 确保时间索引
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        # 确保必要的列存在
        required_cols = ["open", "high", "low", "close", "volume"]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"数据缺少必要列: {col}")
        return data.sort_index()

    def _update_portfolio_value(self, current_row: pd.Series):
        """更新持仓市值"""
        position_value = 0.0
        for _symbol, quantity in self.positions.items():
            position_value += quantity * current_row["close"]
        self.portfolio_value = self.cash + position_value

    def _generate_signals(
        self,
        current_row: pd.Series,
        strategy_def: dict[str, Any],
        historical_data: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """生成交易信号"""
        # 使用SignalGenerator生成信号
        from app.analytics.backtest.signal_generator import SignalGenerator

        signal_generator = SignalGenerator()

        # 生成技术指标信号
        signals = signal_generator.generate_signals(historical_data, strategy_def)

        # 转换信号格式以匹配回测引擎的期望格式
        formatted_signals = []
        for signal in signals:
            action_str = signal.get("action", "buy")
            action = (
                TradeAction.BUY
                if action_str.lower() == "buy"
                else (
                    TradeAction.SELL
                    if action_str.lower() == "sell"
                    else TradeAction.HOLD
                )
            )

            formatted_signals.append(
                {
                    "action": action,
                    "symbol": signal.get("symbol", "default"),
                    "quantity": signal.get("quantity", 1.0),
                }
            )

        return formatted_signals

    def _execute_trades(self, signals: list[dict[str, Any]], current_row: pd.Series):
        """执行交易"""
        if not isinstance(self.current_date, datetime):
            # 当未在回测主循环中设置时间戳时, 提供一个合理的默认时间戳以允许交易执行
            logger.warning(
                "current_date is not a datetime object, using current timestamp for trade execution."
            )
            self.current_date = datetime.now()
        for signal in signals:
            symbol = signal.get("symbol", "default")
            action = signal["action"]
            quantity = signal["quantity"]
            price = current_row["close"]
            commission = quantity * price * self.commission_rate
            if action == TradeAction.BUY:
                cost = quantity * price + commission
                if cost <= self.cash:
                    self.cash -= cost
                    self.positions[symbol] = self.positions.get(symbol, 0.0) + quantity
                    self.trades.append(
                        Trade(
                            symbol,
                            action,
                            quantity,
                            price,
                            self.current_date,
                            commission,
                        )
                    )
            elif action == TradeAction.SELL:
                current_position = self.positions.get(symbol, 0.0)
                if current_position >= quantity:
                    proceeds = quantity * price - commission
                    self.cash += proceeds
                    self.positions[symbol] = current_position - quantity
                    if self.positions[symbol] <= 0:
                        del self.positions[symbol]
                    self.trades.append(
                        Trade(
                            symbol,
                            action,
                            quantity,
                            price,
                            self.current_date,
                            commission,
                        )
                    )

    def _record_equity_curve(self):
        """记录权益曲线"""
        self.equity_curve.append(
            {
                "timestamp": self.current_date,
                "portfolio_value": self.portfolio_value,
                "cash": self.cash,
                "positions": self.positions.copy(),
            }
        )

    def _calculate_performance_metrics(self) -> dict[str, float]:
        """计算性能指标"""
        if not self.equity_curve:
            return {}
        equity_values = [point["portfolio_value"] for point in self.equity_curve]
        returns = (
            np.diff(equity_values) / equity_values[:-1]
            if len(equity_values) > 1
            else np.array([])
        )
        # 总收益率
        total_return = (equity_values[-1] / equity_values[0] - 1) * 100
        # 年化收益率
        days = (
            self.equity_curve[-1]["timestamp"] - self.equity_curve[0]["timestamp"]
        ).days
        annual_return = (1 + total_return / 100) ** (365 / max(days, 1)) - 1
        # 夏普比率 (避免除以0或NaN)
        if len(returns) > 1:
            std = float(np.std(returns))
            sharpe_ratio = (
                float(np.mean(returns) / std * np.sqrt(252)) if std > 0 else 0.0
            )
        else:
            sharpe_ratio = 0.0
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(equity_values)
        # 胜率
        win_rate = self._calculate_win_rate()
        return {
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "win_rate": round(win_rate * 100, 2),
            "total_trades": len(self.trades),
            "profitable_trades": sum(
                1 for trade in self.trades if trade.action == TradeAction.SELL
            ),
        }

    def _calculate_max_drawdown(self, equity_values: list[float]) -> float:
        """计算最大回撤"""
        peak = equity_values[0]
        max_dd = 0.0
        for value in equity_values:
            peak = max(peak, value)
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        return max_dd

    def _calculate_win_rate(self) -> float:
        """计算胜率"""
        if not self.trades:
            return 0.0

        buy_trades = [t for t in self.trades if t.action == TradeAction.BUY]
        if not buy_trades:
            return 0.0

        # 简化计算: 假设卖出交易都是盈利的
        sell_trades = [t for t in self.trades if t.action == TradeAction.SELL]
        return len(sell_trades) / len(buy_trades) if buy_trades else 0.0


def run_grid_backtest(db, config):
    """
    执行网格交易策略回测
    Args:
        db: 数据库会话
        config: GridStrategyConfig对象
    Returns:
        Dict: 包含回测结果的字典
    """
    try:
        # 从数据库获取股票数据
        from sqlalchemy import and_

        from app.infrastructure.database.models import StockData

        # 查询指定时间范围内的股票数据
        stock_data = (
            db.query(StockData)
            .filter(
                and_(
                    StockData.ts_code == config.stock_code,
                    StockData.trade_date >= config.start_date,
                    StockData.trade_date <= config.end_date,
                )
            )
            .order_by(StockData.trade_date)
            .all()
        )

        if not stock_data:
            raise ValueError(
                f"未找到股票 {config.stock_code} 在 {config.start_date} 到 {config.end_date} 期间的数据"
            )

        # 将数据转换为DataFrame
        data = []
        for record in stock_data:
            data.append(
                {
                    "timestamp": record.trade_date,
                    "open": record.open,
                    "high": record.high,
                    "low": record.low,
                    "close": record.close,
                    "volume": record.vol,
                }
            )

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)

        # 创建回测引擎实例
        engine = BacktestEngine(
            initial_capital=config.total_investment,
            commission_rate=config.commission_rate,
        )

        # 定义网格策略
        strategy_def = {
            "type": "grid",
            "upper_price": config.upper_price,
            "lower_price": config.lower_price,
            "grid_count": config.grid_count,
            "on_exceed_upper": config.on_exceed_upper,
            "on_fall_below_lower": config.on_fall_below_lower,
        }

        # 执行回测
        result = engine.run_backtest(df, strategy_def)

        # 格式化结果以匹配预期的API响应格式
        return {
            "total_pnl": result["performance_metrics"].get("total_return", 0),
            "total_return_rate": result["performance_metrics"].get("total_return", 0)
            / 100,
            "annualized_return_rate": result["performance_metrics"].get(
                "annual_return", 0
            )
            / 100,
            "annualized_volatility": result["performance_metrics"].get(
                "sharpe_ratio", 0
            ),
            "sharpe_ratio": result["performance_metrics"].get("sharpe_ratio", 0),
            "max_drawdown": result["performance_metrics"].get("max_drawdown", 0) / 100,
            "win_rate": result["performance_metrics"].get("win_rate", 0) / 100,
            "trade_count": result["performance_metrics"].get("total_trades", 0),
            "chart_data": result["equity_curve"],
            "kline_data": [],  # 需要从原始数据生成
            "transaction_log": result["trades"],
            "strategy_config": config.dict(),
            "market_type": "US_stock",  # 需要从数据库获取实际的市场类型
            "final_holding_quantity": len(result["final_positions"]),
            "average_holding_cost": 0.0,  # 需要计算平均持仓成本
        }

    except Exception as e:
        logger.error(f"网格回测执行失败: {e}")
        raise


def run_grid_optimization(db, config):
    """
    执行网格交易参数优化
    Args:
        db: 数据库会话
        config: GridStrategyOptimizeConfig对象
    Returns:
        Dict: 包含优化结果的字典
    """
    # 这是一个占位符实现, 实际需要实现参数优化逻辑
    logger.warning("网格优化功能尚未实现")
    return {"optimization_results": [], "best_result": {}}
