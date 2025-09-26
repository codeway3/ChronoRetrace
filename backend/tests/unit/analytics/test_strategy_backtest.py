"""
策略与回测模块单元测试
"""

from datetime import datetime
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from app.analytics.backtest.backtester import BacktestEngine, TradeAction
from app.analytics.backtest.signal_generator import SignalGenerator, StrategyTemplates
from app.analytics.models import BacktestResult, Strategy
from app.analytics.schemas.strategy_schema import (
    Action,
    ActionType,
    Condition,
    ConditionType,
    StrategyDefinition,
)
from app.analytics.services.strategy_service import StrategyService


class TestStrategyModels:
    """测试策略数据库模型"""

    def test_strategy_model_creation(self):
        """测试策略模型创建"""
        strategy = Strategy(
            user_id=1,
            name="测试策略",
            description="这是一个测试策略",
            definition={"version": "1.0", "conditions": [], "actions": []},
        )

        assert strategy.user_id == 1
        assert strategy.name == "测试策略"
        assert strategy.description == "这是一个测试策略"
        assert strategy.definition["version"] == "1.0"

    def test_backtest_result_model_creation(self):
        """测试回测结果模型创建"""
        result = BacktestResult(
            strategy_id=1,
            user_id=1,
            symbol="AAPL",
            interval="1d",
            start_date=datetime.now(),
            end_date=datetime.now(),
            initial_capital=100000,
            total_return=15.5,
            annual_return=12.3,
            sharpe_ratio=1.2,
            max_drawdown=8.7,
            win_rate=60.0,
        )

        assert result.strategy_id == 1
        assert result.symbol == "AAPL"
        assert result.total_return == 15.5
        assert result.win_rate == 60.0


class TestStrategySchema:
    """测试策略模式验证"""

    def test_strategy_definition_validation(self):
        """测试策略定义验证"""
        # 有效的策略定义
        strategy_def = StrategyDefinition(
            symbols=["AAPL"],
            interval="1d",
            conditions=[
                Condition(
                    type=ConditionType.TECHNICAL,
                    indicator="sma",
                    operator=">",
                    value=50,
                    lookback_period=20,
                )
            ],
            actions=[Action(type=ActionType.BUY, condition_id=0, position_size=0.5)],
        )

        assert strategy_def.symbols == ["AAPL"]
        assert strategy_def.interval == "1d"
        assert len(strategy_def.conditions) == 1
        assert len(strategy_def.actions) == 1

    def test_invalid_interval_validation(self):
        """测试无效时间间隔验证"""
        with pytest.raises(ValueError):
            StrategyDefinition(
                symbols=["AAPL"], interval="invalid", conditions=[], actions=[]
            )


class TestStrategyService:
    """测试策略服务"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_db = Mock()
        self.service = StrategyService(self.mock_db)

    def test_create_strategy(self):
        """测试创建策略"""
        # 模拟数据库操作
        mock_strategy = Mock()
        mock_strategy.id = 1

        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, "id", 1))

        # 创建策略
        strategy = self.service.create_strategy(
            user_id=1,
            name="测试策略",
            definition={"test": "data"},
            description="测试描述",
        )

        assert strategy.id == 1
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

    def test_get_user_strategies(self):
        """测试获取用户策略"""
        # 模拟查询结果
        mock_strategies = [Mock(), Mock()]
        self.mock_db.query.return_value.filter.return_value.all.return_value = (
            mock_strategies
        )

        strategies = self.service.get_user_strategies(1)

        assert len(strategies) == 2
        self.mock_db.query.assert_called_with(Strategy)


class TestBacktestEngine:
    """测试回测引擎"""

    def setup_method(self):
        """设置测试环境"""
        self.engine = BacktestEngine(initial_capital=100000)

        # 创建测试数据
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        self.test_data = pd.DataFrame(
            {
                "open": np.random.uniform(100, 200, 50),
                "high": np.random.uniform(100, 200, 50),
                "low": np.random.uniform(100, 200, 50),
                "close": np.random.uniform(100, 200, 50),
                "volume": np.random.uniform(100000, 1000000, 50),
            },
            index=dates,
        )

        # 简单策略定义
        self.simple_strategy = {
            "version": "1.0",
            "symbols": ["TEST"],
            "interval": "1d",
            "initial_capital": 100000,
            "conditions": [],
            "actions": [],
            "max_position_size": 0.2,
        }

    def test_engine_initialization(self):
        """测试引擎初始化"""
        assert self.engine.initial_capital == 100000
        assert self.engine.cash == 100000
        assert self.engine.portfolio_value == 100000
        assert len(self.engine.positions) == 0
        assert len(self.engine.trades) == 0

    def test_data_preprocessing(self):
        """测试数据预处理"""
        processed_data = self.engine._preprocess_data(self.test_data)

        assert isinstance(processed_data.index, pd.DatetimeIndex)
        assert len(processed_data) == 50

        # 测试缺少必要列的情况
        invalid_data = self.test_data.drop(columns=["close"])
        with pytest.raises(ValueError):
            self.engine._preprocess_data(invalid_data)

    def test_portfolio_value_update(self):
        """测试持仓市值更新"""
        # 设置持仓
        self.engine.positions = {"TEST": 100}
        current_row = pd.Series({"close": 150.0})

        self.engine._update_portfolio_value(current_row)

        assert self.engine.portfolio_value == 100000 + (100 * 150.0)

    def test_trade_execution_buy(self):
        """测试买入交易执行"""
        current_row = pd.Series({"close": 150.0})
        signals = [{"action": TradeAction.BUY, "symbol": "TEST", "quantity": 100}]

        self.engine._execute_trades(signals, current_row)

        assert len(self.engine.trades) == 1
        assert self.engine.positions["TEST"] == 100
        assert self.engine.cash < 100000  # 现金减少

    def test_trade_execution_sell(self):
        """测试卖出交易执行"""
        # 先买入
        self.engine.positions = {"TEST": 100}
        self.engine.cash = 50000

        current_row = pd.Series({"close": 160.0})
        signals = [{"action": TradeAction.SELL, "symbol": "TEST", "quantity": 100}]

        self.engine._execute_trades(signals, current_row)

        assert len(self.engine.trades) == 1
        assert "TEST" not in self.engine.positions  # 持仓清空
        assert self.engine.cash > 50000  # 现金增加

    def test_performance_metrics_calculation(self):
        """测试性能指标计算"""
        # 设置权益曲线
        self.engine.equity_curve = [
            {"timestamp": datetime(2023, 1, 1), "portfolio_value": 100000},
            {"timestamp": datetime(2023, 1, 2), "portfolio_value": 105000},
            {"timestamp": datetime(2023, 1, 3), "portfolio_value": 103000},
            {"timestamp": datetime(2023, 1, 4), "portfolio_value": 107000},
        ]

        metrics = self.engine._calculate_performance_metrics()

        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert metrics["total_return"] > 0  # 应该有正收益

    def test_max_drawdown_calculation(self):
        """测试最大回撤计算"""
        equity_values = [100000, 120000, 90000, 110000, 85000, 95000]
        max_dd = self.engine._calculate_max_drawdown(equity_values)

        # 最大回撤应该是从120000到85000的回撤
        expected_dd = (120000 - 85000) / 120000
        assert abs(max_dd - expected_dd) < 1e-6


class TestSignalGenerator:
    """测试信号生成器"""

    def setup_method(self):
        """设置测试环境"""
        # 创建测试数据
        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        self.test_data = pd.DataFrame(
            {
                "open": np.linspace(100, 200, 30),
                "high": np.linspace(105, 205, 30),
                "low": np.linspace(95, 195, 30),
                "close": np.linspace(100, 200, 30),
                "volume": np.random.uniform(100000, 500000, 30),
            },
            index=dates,
        )

        self.current_data = self.test_data.iloc[-1]
        self.historical_data = self.test_data

    def test_sma_calculation(self):
        """测试SMA计算"""
        condition = {"indicator": "sma", "window": 10}
        sma_value = SignalGenerator._calculate_indicator(self.test_data, condition)
        expected_sma = self.test_data["close"].rolling(window=10).mean().iloc[-1]

        assert abs(sma_value - expected_sma) < 1e-6

    def test_rsi_calculation(self):
        """测试RSI计算"""
        condition = {"indicator": "rsi", "window": 14}
        rsi_value = SignalGenerator._calculate_indicator(self.test_data, condition)

        # RSI应该在0-100之间
        assert 0 <= rsi_value <= 100

    def test_condition_evaluation(self):
        """测试条件评估"""
        condition = {"indicator": "sma", "window": 10, "operator": "gt", "value": 150}

        result = SignalGenerator._evaluate_condition(self.test_data, condition)

        # 由于收盘价从100到200线性增长，最后一天的SMA应该大于150
        assert result

    def test_strategy_templates(self):
        """测试策略模板"""
        ma_strategy = StrategyTemplates.moving_average_crossover()
        rsi_strategy = StrategyTemplates.rsi_strategy()

        # 检查策略类型和结构
        assert ma_strategy["type"] == "technical"
        assert rsi_strategy["type"] == "technical"
        assert len(ma_strategy["conditions"]) == 2
        assert len(rsi_strategy["conditions"]) == 2
        # 检查条件中的action字段
        assert ma_strategy["conditions"][0]["action"] == "buy"
        assert ma_strategy["conditions"][1]["action"] == "sell"
        assert rsi_strategy["conditions"][0]["action"] == "buy"
        assert rsi_strategy["conditions"][1]["action"] == "sell"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
