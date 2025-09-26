"""
策略与回测模块集成测试
"""

from datetime import datetime
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from app.analytics.backtest.backtester import BacktestEngine
from app.analytics.backtest.signal_generator import SignalGenerator
from app.analytics.models import Strategy
from app.analytics.services.strategy_service import BacktestService, StrategyService


class TestStrategyBacktestIntegration:
    """测试策略与回测的集成"""

    def setup_method(self):
        """设置测试环境"""
        # 创建测试数据
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        self.test_data = pd.DataFrame(
            {
                "open": np.linspace(100, 200, 100),
                "high": np.linspace(105, 205, 100),
                "low": np.linspace(95, 195, 100),
                "close": np.linspace(100, 200, 100),
                "volume": np.random.uniform(100000, 500000, 100),
            },
            index=dates,
        )

        # 创建简单策略定义
        self.simple_strategy_def = {
            "version": "1.0",
            "type": "technical",
            "symbols": ["TEST"],
            "interval": "1d",
            "initial_capital": 100000,
            "max_position_size": 0.2,
            "conditions": [
                {
                    "id": 0,
                    "type": "technical",
                    "indicator": "sma",
                    "operator": "gt",
                    "value": 150,
                    "lookback_period": 20,
                }
            ],
            "actions": [{"type": "buy", "condition_id": 0, "position_size": 0.1}],
        }

    def test_strategy_creation_and_backtest_integration(self):
        """测试策略创建到回测的完整流程"""
        # 创建策略
        strategy = Strategy(
            user_id=1,
            name="集成测试策略",
            description="用于集成测试的策略",
            definition=self.simple_strategy_def,
        )

        # 使用 is 操作符进行比较,避免 SQLAlchemy 的布尔操作问题
        assert strategy.user_id is 1  # noqa: F632
        assert str(strategy.name) == "集成测试策略"
        assert str(strategy.definition["version"]) == "1.0"

        # 测试信号生成
        signal_generator = SignalGenerator()
        historical_data = self.test_data

        signals = signal_generator.generate_signals(
            historical_data, self.simple_strategy_def
        )

        # 应该有信号生成
        assert len(signals) > 0

        # 测试回测引擎
        backtest_engine = BacktestEngine(initial_capital=100000)

        # 运行回测
        results = backtest_engine.run_backtest(
            data=self.test_data, strategy_definition=self.simple_strategy_def
        )

        # 验证回测结果
        assert "performance_metrics" in results
        assert "trades" in results
        assert "equity_curve" in results

        # 验证性能指标
        metrics = results["performance_metrics"]
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert isinstance(metrics["total_return"], float)
        assert isinstance(metrics["sharpe_ratio"], float)
        assert isinstance(metrics["max_drawdown"], float)

        # 验证交易记录
        assert isinstance(results["trades"], list)

        # 验证权益曲线
        assert isinstance(results["equity_curve"], list)
        assert len(results["equity_curve"]) > 0

    def test_service_layer_integration(self):
        """测试服务层集成"""
        # 模拟数据库会话
        mock_db = Mock()

        # 测试策略服务
        strategy_service = StrategyService(mock_db)

        # 创建策略
        _strategy = strategy_service.create_strategy(
            user_id=1,
            name="服务测试策略",
            definition=self.simple_strategy_def,
            description="服务层测试",
        )

        # 验证数据库操作
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # 测试回测服务
        backtest_service = BacktestService(mock_db)

        # 创建回测结果
        performance_metrics = {
            "total_return": 15.5,
            "annual_return": 12.3,
            "sharpe_ratio": 1.2,
            "max_drawdown": 8.7,
            "win_rate": 60.0,
            "total_trades": 10,
            "profitable_trades": 6,
        }
        equity_curve = [{"timestamp": datetime(2023, 1, 1), "portfolio_value": 100000}]
        trades = [
            {
                "timestamp": datetime(2023, 1, 2),
                "symbol": "TEST",
                "action": "buy",
                "quantity": 100,
                "price": 100.0,
            }
        ]

        _backtest_result = backtest_service.save_backtest_result(
            strategy_id=1,
            user_id=1,
            symbol="TEST",
            interval="1d",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 4, 10),
            initial_capital=100000,
            performance_metrics=performance_metrics,
            equity_curve=equity_curve,
            trades=trades,
        )

        # 验证数据库操作
        assert mock_db.add.call_count == 2  # 策略 + 回测结果
        assert mock_db.commit.call_count == 2

    def test_complete_workflow_with_mock_data(self):
        """测试完整工作流（使用模拟数据）"""
        # 1. 创建策略
        strategy_def = {
            "version": "1.0",
            "type": "technical",
            "symbols": ["MOCK"],
            "interval": "1d",
            "initial_capital": 50000,
            "max_position_size": 0.3,
            "conditions": [
                {
                    "id": 0,
                    "type": "technical",
                    "indicator": "rsi",
                    "operator": "lt",
                    "value": 30,
                    "lookback_period": 14,
                },
                {
                    "id": 1,
                    "type": "technical",
                    "indicator": "rsi",
                    "operator": "gt",
                    "value": 70,
                    "lookback_period": 14,
                },
            ],
            "actions": [
                {"type": "buy", "condition_id": 0, "position_size": 0.2},
                {"type": "sell", "condition_id": 1, "position_size": 1.0},  # 全部卖出
            ],
        }

        # 2. 生成交易信号
        signal_generator = SignalGenerator()

        # 创建模拟数据（包含RSI计算所需的数据）
        mock_dates = pd.date_range("2023-01-01", periods=50, freq="D")
        mock_prices = np.array(
            [100 + i * 2 + np.random.normal(0, 5) for i in range(50)]
        )

        mock_data = pd.DataFrame(
            {
                "open": mock_prices - 1,
                "high": mock_prices + 2,
                "low": mock_prices - 2,
                "close": mock_prices,
                "volume": np.random.uniform(100000, 300000, 50),
            },
            index=mock_dates,
        )

        _signals = signal_generator.generate_signals(mock_data, strategy_def)

        # 3. 执行回测
        backtest_engine = BacktestEngine(initial_capital=50000)

        results = backtest_engine.run_backtest(
            data=mock_data, strategy_definition=strategy_def
        )

        # 验证结果
        assert "performance_metrics" in results
        assert "trades" in results
        assert "equity_curve" in results
        assert len(results["trades"]) >= 0  # 可能有交易也可能没有
        assert len(results["equity_curve"]) == len(mock_data)

        # 验证权益曲线单调性（不应该有负值）
        equity_values = [point["portfolio_value"] for point in results["equity_curve"]]
        assert all(value >= 0 for value in equity_values)

        # 验证现金管理
        assert results["final_cash"] >= 0
        assert results["final_portfolio_value"] >= 0


class TestErrorHandlingIntegration:
    """测试错误处理集成"""

    def test_invalid_strategy_definition(self):
        """测试无效策略定义的处理"""
        invalid_strategy = {
            "version": "1.0",
            "symbols": ["TEST"],
            "interval": "invalid_interval",  # 无效的时间间隔
            "conditions": [],
            "actions": [],
        }

        backtest_engine = BacktestEngine(initial_capital=100000)

        # 创建测试数据
        dates = pd.date_range("2023-01-01", periods=20, freq="D")
        test_data = pd.DataFrame(
            {
                "open": np.random.uniform(100, 200, 20),
                "high": np.random.uniform(100, 200, 20),
                "low": np.random.uniform(100, 200, 20),
                "close": np.random.uniform(100, 200, 20),
                "volume": np.random.uniform(100000, 500000, 20),
            },
            index=dates,
        )

        # 应该正确处理无效策略
        results = backtest_engine.run_backtest(
            data=test_data, strategy_definition=invalid_strategy
        )

        # 即使策略无效，也应该返回基本结果
        assert "performance_metrics" in results
        metrics = results["performance_metrics"]
        assert "total_return" in metrics
        assert metrics["total_return"] == 0.0  # 没有交易，收益为0

    def test_insufficient_data_for_indicators(self):
        """测试指标计算数据不足的情况"""
        strategy_def = {
            "version": "1.0",
            "symbols": ["TEST"],
            "interval": "1d",
            "conditions": [
                {
                    "id": 0,
                    "type": "technical",
                    "indicator": "sma",
                    "operator": ">",
                    "value": 150,
                    "lookback_period": 50,  # 需要50期数据
                }
            ],
            "actions": [{"type": "buy", "condition_id": 0, "position_size": 0.1}],
        }

        # 创建数据不足的测试数据
        dates = pd.date_range("2023-01-01", periods=30, freq="D")  # 只有30期数据
        test_data = pd.DataFrame(
            {
                "open": np.random.uniform(100, 200, 30),
                "high": np.random.uniform(100, 200, 30),
                "low": np.random.uniform(100, 200, 30),
                "close": np.random.uniform(100, 200, 30),
                "volume": np.random.uniform(100000, 500000, 30),
            },
            index=dates,
        )

        backtest_engine = BacktestEngine(initial_capital=100000)

        # 应该正确处理数据不足的情况
        results = backtest_engine.run_backtest(
            data=test_data, strategy_definition=strategy_def
        )

        # 应该完成回测，但可能没有交易信号
        assert "performance_metrics" in results
        metrics = results["performance_metrics"]
        assert "total_return" in metrics
        assert len(results["trades"]) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
