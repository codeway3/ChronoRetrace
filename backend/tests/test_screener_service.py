#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选器服务的单元测试
"""

from unittest.mock import MagicMock as Mock

import pytest

from app.db.models import DailyStockMetrics
from app.schemas.stock import ScreenerCondition, StockScreenerRequest
from app.services.screener_service import (get_operator_expression,
                                           screen_stocks)


class TestScreenerService:
    """筛选器服务测试"""

    def test_get_operator_expression(self):
        """测试操作符表达式生成（使用真实的 SQLAlchemy 列以避免 Mock 的比较运算问题）"""
        from sqlalchemy.sql.elements import BinaryExpression

        column = DailyStockMetrics.pe_ratio

        assert isinstance(get_operator_expression(column, "gt", 10), BinaryExpression)
        assert isinstance(get_operator_expression(column, "lt", 20), BinaryExpression)
        assert isinstance(get_operator_expression(column, "eq", 15), BinaryExpression)
        assert isinstance(get_operator_expression(column, "gte", 25), BinaryExpression)
        assert isinstance(get_operator_expression(column, "lte", 30), BinaryExpression)

        with pytest.raises(ValueError, match="Unsupported operator: invalid"):
            get_operator_expression(column, "invalid", 100)

    def test_screen_stocks_no_conditions(self):
        """测试无筛选条件的情况"""
        # 创建模拟数据
        mock_db = Mock()
        mock_metrics = [
            Mock(
                code="000001.SZ",
                pe_ratio=15.2,
                market_cap=250000000000,
                close_price=12.50,
                ma5=12.8,
                ma20=13.2,
                volume=50000000,
            ),
            Mock(
                code="000002.SZ",
                pe_ratio=12.5,
                market_cap=200000000000,
                close_price=18.30,
                ma5=18.5,
                ma20=19.1,
                volume=30000000,
            ),
        ]

        # 设置模拟查询链
        query_mock = Mock()
        filter_mock = Mock()
        join_mock = Mock()
        limit_mock = Mock()
        offset_mock = Mock()

        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.group_by.return_value = Mock()
        filter_mock.group_by.return_value.subquery.return_value = Mock()

        query_mock.join.return_value = join_mock
        join_mock.join.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.count.return_value = 2
        filter_mock.limit.return_value = limit_mock
        limit_mock.offset.return_value = offset_mock
        offset_mock.all.return_value = [
            (mock_metrics[0], "平安银行"),
            (mock_metrics[1], "万科A"),
        ]

        # 创建请求
        request = StockScreenerRequest(market="A_share", conditions=[], page=1, size=20)

        # 执行测试
        result = screen_stocks(mock_db, request)

        # 验证结果
        assert result.total == 2
        assert result.page == 1
        assert result.size == 20
        assert len(result.items) == 2

        # 验证第一只股票
        assert result.items[0].code == "000001.SZ"
        assert result.items[0].name == "平安银行"
        assert result.items[0].pe_ratio == 15.2
        assert result.items[0].market_cap == 250000000000

        # 验证第二只股票
        assert result.items[1].code == "000002.SZ"
        assert result.items[1].name == "万科A"
        assert result.items[1].pe_ratio == 12.5
        assert result.items[1].market_cap == 200000000000

    def test_screen_stocks_with_pe_filter(self):
        """测试市盈率筛选"""
        # 创建模拟数据
        mock_db = Mock()
        mock_metrics = [
            Mock(
                code="000001.SZ",
                pe_ratio=15.2,
                market_cap=250000000000,
                close_price=12.50,
                ma5=12.8,
                ma20=13.2,
                volume=50000000,
            ),
            Mock(
                code="000002.SZ",
                pe_ratio=12.5,
                market_cap=200000000000,
                close_price=18.30,
                ma5=18.5,
                ma20=19.1,
                volume=30000000,
            ),
        ]

        # 设置模拟查询链
        query_mock = Mock()
        filter_mock = Mock()
        join_mock = Mock()
        limit_mock = Mock()
        offset_mock = Mock()

        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.group_by.return_value = Mock()
        filter_mock.group_by.return_value.subquery.return_value = Mock()

        query_mock.join.return_value = join_mock
        join_mock.join.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.count.return_value = 2
        filter_mock.limit.return_value = limit_mock
        limit_mock.offset.return_value = offset_mock
        offset_mock.all.return_value = [
            (mock_metrics[0], "平安银行"),
            (mock_metrics[1], "万科A"),
        ]

        # 创建请求
        request = StockScreenerRequest(
            market="A_share",
            conditions=[ScreenerCondition(field="pe_ratio", operator="lt", value=20.0)],
            page=1,
            size=20,
        )

        # 执行测试
        result = screen_stocks(mock_db, request)

        # 验证结果
        assert result.total == 2
        assert len(result.items) == 2

        # 验证筛选结果：PE < 20 的股票
        assert result.items[0].pe_ratio == 15.2  # 平安银行
        assert result.items[1].pe_ratio == 12.5  # 万科A

    def test_screen_stocks_pagination(self):
        """测试分页功能"""
        # 创建模拟数据
        mock_db = Mock()
        mock_metrics = [
            Mock(
                code="000001.SZ",
                pe_ratio=15.2,
                market_cap=250000000000,
                close_price=12.50,
                ma5=12.8,
                ma20=13.2,
                volume=50000000,
            ),
        ]

        # 设置模拟查询链
        query_mock = Mock()
        filter_mock = Mock()
        join_mock = Mock()
        limit_mock = Mock()
        offset_mock = Mock()

        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.group_by.return_value = Mock()
        filter_mock.group_by.return_value.subquery.return_value = Mock()

        query_mock.join.return_value = join_mock
        join_mock.join.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock
        filter_mock.count.return_value = 3  # 总共有3条记录
        filter_mock.limit.return_value = limit_mock
        limit_mock.offset.return_value = offset_mock
        offset_mock.all.return_value = [
            (mock_metrics[0], "平安银行"),
        ]

        # 创建请求
        request = StockScreenerRequest(
            market="A_share",
            conditions=[],
            page=1,
            size=1,  # 每页1条
        )

        # 执行测试
        result = screen_stocks(mock_db, request)

        # 验证结果
        assert result.total == 3
        assert result.page == 1
        assert result.size == 1
        assert len(result.items) == 1


if __name__ == "__main__":
    pytest.main([__file__])
