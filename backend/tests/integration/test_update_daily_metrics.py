#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票指标数据更新任务的单元测试
"""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database.models import DailyStockMetrics
from app.jobs.update_daily_metrics import (
    calculate_technical_metrics,
    fetch_a_share_fundamentals,
    update_metrics_for_market,
)


class TestCalculateTechnicalMetrics:
    """测试技术指标计算函数"""

    def test_calculate_technical_metrics_success(self):
        """测试成功计算技术指标"""
        # 创建测试数据
        dates = pd.date_range(start="2025-01-01", periods=25, freq="D")
        df = pd.DataFrame(
            {
                "trade_date": dates,
                "close": [100 + i for i in range(25)],
                "vol": [1000000 + i * 10000 for i in range(25)],
            }
        )

        result = calculate_technical_metrics(df)

        assert result is not None
        assert result["close_price"] == 124.0  # 最后一天的价格
        assert result["ma5"] == 122.0  # 最后5天的平均值 (120, 121, 122, 123, 124)
        assert result["ma20"] == 114.5  # 最后20天的平均值 (100到119的平均值)
        assert result["volume"] == 1240000  # 最后一天的成交量 (1000000 + 24 * 10000)

    def test_calculate_technical_metrics_empty_dataframe(self):
        """测试空数据框"""
        df = pd.DataFrame()
        result = calculate_technical_metrics(df)
        assert result is None

    def test_calculate_technical_metrics_insufficient_data(self):
        """测试数据不足（少于20天）"""
        dates = pd.date_range(start="2025-01-01", periods=15, freq="D")
        df = pd.DataFrame(
            {
                "trade_date": dates,
                "close": [100 + i for i in range(15)],
                "vol": [1000000 + i * 10000 for i in range(15)],
            }
        )

        result = calculate_technical_metrics(df)
        assert result is None

    def test_calculate_technical_metrics_with_date_column(self):
        """测试使用date列而不是trade_date列"""
        dates = pd.date_range(start="2025-01-01", periods=25, freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "close": [100 + i for i in range(25)],
                "vol": [1000000 + i * 10000 for i in range(25)],
            }
        )

        result = calculate_technical_metrics(df)
        assert result is not None
        assert result["close_price"] == 124.0

    def test_calculate_technical_metrics_with_nan_values(self):
        """测试包含NaN值的数据"""
        dates = pd.date_range(start="2025-01-01", periods=25, freq="D")
        df = pd.DataFrame(
            {
                "trade_date": dates,
                "close": [100 + i if i < 20 else None for i in range(25)],
                "vol": [1000000 + i * 10000 if i < 20 else None for i in range(25)],
            }
        )

        result = calculate_technical_metrics(df)
        assert result is not None
        assert result["close_price"] is None  # 最后一天是NaN
        assert result["volume"] is None


class TestFetchAShareFundamentals:
    """测试A股基本面数据获取函数"""

    @pytest.mark.asyncio
    async def test_fetch_a_share_fundamentals_success(self):
        """测试成功获取A股基本面数据"""
        result = await fetch_a_share_fundamentals("000001.SZ")

        assert isinstance(result, dict)
        assert "pe_ratio" in result
        assert "pb_ratio" in result
        assert "market_cap" in result
        assert "dividend_yield" in result

    @pytest.mark.asyncio
    async def test_fetch_a_share_fundamentals_exception_handling(self):
        """测试异常处理"""
        # 模拟异常情况
        with patch("app.jobs.update_daily_metrics.logger"):
            # 这里可以模拟具体的异常情况
            result = await fetch_a_share_fundamentals("INVALID_CODE")

            assert isinstance(result, dict)
            assert len(result) == 4  # 返回4个字段，都是None


class TestUpdateMetricsForMarket:
    """测试市场指标更新函数"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        db = Mock(spec=Session)
        return db

    @pytest.fixture
    def mock_stocks(self):
        """创建模拟股票数据"""
        return [
            Mock(ts_code="000001.SZ"),
            Mock(ts_code="000002.SZ"),
            Mock(ts_code="600519.SH"),
        ]

    @pytest.fixture
    def mock_dataframe(self):
        """创建模拟K线数据"""
        dates = pd.date_range(start="2025-01-01", periods=25, freq="D")
        return pd.DataFrame(
            {
                "trade_date": dates,
                "close": [100 + i for i in range(25)],
                "vol": [1000000 + i * 10000 for i in range(25)],
            }
        )

    @pytest.mark.asyncio
    async def test_update_metrics_for_market_success(
        self, mock_db, mock_stocks, mock_dataframe
    ):
        """测试成功更新市场指标"""
        # 设置模拟
        mock_db.query.return_value.filter.return_value.all.return_value = mock_stocks

        # 模拟数据获取
        with (
            patch("app.jobs.update_daily_metrics.asyncio.to_thread") as mock_to_thread,
            patch(
                "app.jobs.update_daily_metrics.fetch_a_share_fundamentals",
                new_callable=AsyncMock,
            ) as mock_fetch_fundamentals,
            patch(
                "app.jobs.update_daily_metrics.calculate_technical_metrics"
            ) as mock_calc_metrics,
        ):
            # 设置返回值
            mock_to_thread.return_value = mock_dataframe
            mock_fetch_fundamentals.return_value = {
                "pe_ratio": 15.2,
                "pb_ratio": 1.8,
                "market_cap": 250000000000,
                "dividend_yield": 3.5,
            }
            mock_calc_metrics.return_value = {
                "close_price": 124.0,
                "ma5": 120.0,
                "ma20": 110.0,
                "volume": 10240000,
            }

            # 模拟数据库查询
            mock_db.query.return_value.filter.return_value.first.return_value = None

            # 执行测试
            result = await update_metrics_for_market(mock_db, "A_share")

            # 验证结果
            assert result == 3  # 3只股票都成功更新
            assert mock_db.add.call_count == 3  # 添加了3条新记录
            assert mock_db.commit.call_count == 1  # 提交了1次

    @pytest.mark.asyncio
    async def test_update_metrics_for_market_no_data(self, mock_db, mock_stocks):
        """测试没有数据的情况"""
        mock_db.query.return_value.filter.return_value.all.return_value = mock_stocks

        with patch("app.jobs.update_daily_metrics.asyncio.to_thread") as mock_to_thread:
            # 模拟返回空数据
            mock_to_thread.return_value = pd.DataFrame()

            result = await update_metrics_for_market(mock_db, "A_share")

            assert result == 0  # 没有股票被更新
            assert mock_db.add.call_count == 0

    @pytest.mark.asyncio
    async def test_update_metrics_for_market_update_existing(
        self, mock_db, mock_stocks, mock_dataframe
    ):
        """测试更新现有记录"""
        mock_db.query.return_value.filter.return_value.all.return_value = mock_stocks

        # 模拟现有记录
        existing_metrics = Mock(spec=DailyStockMetrics)
        mock_db.query.return_value.filter.return_value.first.return_value = (
            existing_metrics
        )

        with (
            patch("app.jobs.update_daily_metrics.asyncio.to_thread") as mock_to_thread,
            patch(
                "app.jobs.update_daily_metrics.fetch_a_share_fundamentals",
                new_callable=AsyncMock,
            ) as mock_fetch_fundamentals,
            patch(
                "app.jobs.update_daily_metrics.calculate_technical_metrics"
            ) as mock_calc_metrics,
        ):
            mock_to_thread.return_value = mock_dataframe
            mock_fetch_fundamentals.return_value = {
                "pe_ratio": 15.2,
                "pb_ratio": 1.8,
                "market_cap": 250000000000,
                "dividend_yield": 3.5,
            }
            mock_calc_metrics.return_value = {
                "close_price": 124.0,
                "ma5": 120.0,
                "ma20": 110.0,
                "volume": 10240000,
            }

            result = await update_metrics_for_market(mock_db, "A_share")

            assert result == 3
            assert mock_db.add.call_count == 0  # 没有添加新记录
            assert mock_db.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_update_metrics_for_market_exception_handling(
        self, mock_db, mock_stocks
    ):
        """测试异常处理"""
        mock_db.query.return_value.filter.return_value.all.return_value = mock_stocks

        with patch("app.jobs.update_daily_metrics.asyncio.to_thread") as mock_to_thread:
            # 模拟异常
            mock_to_thread.side_effect = Exception("API Error")

            result = await update_metrics_for_market(mock_db, "A_share")

            assert result == 0  # 没有股票被更新
            assert mock_db.commit.call_count == 1  # 仍然会提交（空提交）


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整的工作流程"""
        # 这里可以添加更复杂的集成测试
        # 比如测试整个数据更新流程
        pass


if __name__ == "__main__":
    pytest.main([__file__])
