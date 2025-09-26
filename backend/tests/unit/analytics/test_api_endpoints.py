"""
策略与回测API端点单元测试
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    return Mock()


@pytest.fixture
def mock_strategy_service():
    """模拟策略服务"""
    with patch("app.analytics.api.endpoints.StrategyService") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_backtest_service():
    """模拟回测服务"""
    with patch("app.analytics.api.endpoints.BacktestService") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


class TestStrategyAPI:
    """测试策略API端点"""

    def test_create_strategy_success(self, client, mock_strategy_service):
        """测试成功创建策略"""
        # 模拟服务返回
        mock_strategy = Mock()
        mock_strategy.id = 1
        mock_strategy.name = "测试策略"
        mock_strategy.description = "测试描述"
        mock_strategy.definition = {"version": "1.0"}
        mock_strategy.user_id = 1
        mock_strategy.created_at = datetime.now()
        mock_strategy.updated_at = datetime.now()

        mock_strategy_service.create_strategy.return_value = mock_strategy

        # 请求数据
        payload = {
            "name": "测试策略",
            "description": "测试描述",
            "definition": {
                "version": "1.0",
                "symbols": ["AAPL"],
                "interval": "1d",
                "conditions": [],
                "actions": [],
            },
        }

        response = client.post("/api/analytics/strategies", json=payload)

        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["name"] == "测试策略"
        mock_strategy_service.create_strategy.assert_called_once()

    def test_create_strategy_invalid_data(self, client):
        """测试创建策略时无效数据"""
        # 缺少必要字段
        payload = {"name": "测试策略"}

        response = client.post("/api/analytics/strategies", json=payload)

        assert response.status_code == 422  # 验证错误

    def test_get_all_strategies(self, client, mock_strategy_service):
        """测试获取所有策略"""
        # 模拟返回策略列表
        mock_strategy = Mock()
        mock_strategy.id = 1
        mock_strategy.name = "策略1"

        mock_strategy_service.get_user_strategies.return_value = [mock_strategy]

        response = client.get("/api/analytics/strategies?user_id=1")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "策略1"
        mock_strategy_service.get_user_strategies.assert_called_once_with(1)

    def test_get_strategy_by_id(self, client, mock_strategy_service):
        """测试根据ID获取策略"""
        mock_strategy = Mock()
        mock_strategy.id = 1
        mock_strategy.name = "测试策略"

        mock_strategy_service.get_strategy.return_value = mock_strategy

        response = client.get("/api/analytics/strategies/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1
        mock_strategy_service.get_strategy.assert_called_once_with(1)

    def test_get_strategy_not_found(self, client, mock_strategy_service):
        """测试获取不存在的策略"""
        mock_strategy_service.get_strategy.return_value = None

        response = client.get("/api/analytics/strategies/999")

        assert response.status_code == 404
        assert "Strategy not found" in response.json()["detail"]

    def test_update_strategy(self, client, mock_strategy_service):
        """测试更新策略"""
        mock_strategy = Mock()
        mock_strategy.id = 1
        mock_strategy.name = "更新后的策略"

        mock_strategy_service.update_strategy.return_value = mock_strategy

        payload = {"name": "更新后的策略", "description": "更新后的描述"}

        response = client.put("/api/analytics/strategies/1", json=payload)

        assert response.status_code == 200
        assert response.json()["name"] == "更新后的策略"
        mock_strategy_service.update_strategy.assert_called_once()

    def test_delete_strategy(self, client, mock_strategy_service):
        """测试删除策略"""
        mock_strategy_service.delete_strategy.return_value = True

        response = client.delete("/api/analytics/strategies/1")

        assert response.status_code == 200
        assert response.json()["message"] == "Strategy deleted successfully"
        mock_strategy_service.delete_strategy.assert_called_once_with(1)


class TestBacktestAPI:
    """测试回测API端点"""

    def test_get_all_backtest_results(self, client, mock_backtest_service):
        """测试获取所有回测结果"""
        mock_result = Mock()
        mock_result.id = 1
        mock_result.strategy_id = 1
        mock_result.symbol = "AAPL"

        mock_backtest_service.get_user_backtest_results.return_value = [mock_result]

        response = client.get("/api/analytics/backtest/results?user_id=1")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["symbol"] == "AAPL"
        mock_backtest_service.get_user_backtest_results.assert_called_once_with(1)

    def test_get_backtest_result_by_id(self, client, mock_backtest_service):
        """测试根据ID获取回测结果"""
        mock_result = Mock()
        mock_result.id = 1
        mock_result.strategy_id = 1
        mock_result.total_return = 15.5

        mock_backtest_service.get_backtest_result.return_value = mock_result

        response = client.get("/api/analytics/backtest/results/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["total_return"] == 15.5
        mock_backtest_service.get_backtest_result.assert_called_once_with(1)

    def test_get_backtest_result_not_found(self, client, mock_backtest_service):
        """测试获取不存在的回测结果"""
        mock_backtest_service.get_backtest_result.return_value = None

        response = client.get("/api/analytics/backtest/results/999")

        assert response.status_code == 404
        assert "Backtest result not found" in response.json()["detail"]


class TestBacktestExecution:
    """测试回测执行端点"""

    @patch("app.analytics.api.endpoints.BacktestEngine")
    def test_run_backtest_success(
        self, mock_backtest_engine, client, mock_strategy_service
    ):
        """测试成功执行回测"""
        # 模拟策略
        mock_strategy = Mock()
        mock_strategy.id = 1
        mock_strategy.definition = {
            "symbols": ["AAPL"],
            "interval": "1d",
            "conditions": [],
            "actions": [],
        }
        mock_strategy_service.get_strategy.return_value = mock_strategy

        # 模拟回测引擎
        mock_engine_instance = Mock()
        mock_engine_instance.run.return_value = {
            "total_return": 12.5,
            "sharpe_ratio": 1.2,
            "max_drawdown": 8.3,
        }
        mock_backtest_engine.return_value = mock_engine_instance

        # 模拟回测服务
        mock_backtest_result = Mock()
        mock_backtest_result.id = 1

        with patch(
            "app.analytics.api.endpoints.BacktestService"
        ) as mock_backtest_service_class:
            mock_backtest_service = Mock()
            mock_backtest_service.create_backtest_result.return_value = (
                mock_backtest_result
            )
            mock_backtest_service_class.return_value = mock_backtest_service

            # 执行回测
            payload = {
                "symbol": "AAPL",
                "interval": "1d",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 100000,
            }

            response = client.post("/api/analytics/strategies/1/backtest", json=payload)

            assert response.status_code == 200
            assert response.json()["id"] == 1
            mock_engine_instance.run.assert_called_once()
            mock_backtest_service.create_backtest_result.assert_called_once()

    def test_run_backtest_strategy_not_found(self, client, mock_strategy_service):
        """测试执行回测时策略不存在"""
        mock_strategy_service.get_strategy.return_value = None

        payload = {
            "symbol": "AAPL",
            "interval": "1d",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
        }

        response = client.post("/api/analytics/strategies/999/backtest", json=payload)

        assert response.status_code == 404
        assert "Strategy not found" in response.json()["detail"]

    def test_run_backtest_invalid_parameters(self, client):
        """测试执行回测时参数无效"""
        # 缺少必要参数
        payload = {"symbol": "AAPL"}

        response = client.post("/api/analytics/strategies/1/backtest", json=payload)

        assert response.status_code == 422  # 验证错误


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
