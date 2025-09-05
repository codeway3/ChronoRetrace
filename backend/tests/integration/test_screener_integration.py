#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选器功能的集成测试
"""

from datetime import date
from unittest.mock import Mock

import pytest

from app.schemas.stock import ScreenerCondition, StockScreenerRequest
from app.analytics.screener.screener_service import screen_stocks


class TestScreenerIntegration:
    """筛选器集成测试"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        db = Mock()
        return db

    @pytest.fixture
    def sample_stocks(self):
        """示例股票数据"""
        return [
            Mock(ts_code="000001.SZ", name="平安银行"),
            Mock(ts_code="000002.SZ", name="万科A"),
            Mock(ts_code="600519.SH", name="贵州茅台"),
        ]

    @pytest.fixture
    def sample_metrics(self):
        """示例指标数据"""
        return [
            Mock(
                code="000001.SZ",
                market="A_share",
                date=date.today(),
                pe_ratio=15.2,
                market_cap=250000000000,
                close_price=12.50,
                ma5=12.8,
                ma20=13.2,
                volume=50000000,
            ),
            Mock(
                code="000002.SZ",
                market="A_share",
                date=date.today(),
                pe_ratio=12.5,
                market_cap=200000000000,
                close_price=18.30,
                ma5=18.5,
                ma20=19.1,
                volume=30000000,
            ),
            Mock(
                code="600519.SH",
                market="A_share",
                date=date.today(),
                pe_ratio=45.2,
                market_cap=1980000000000,
                close_price=1580.00,
                ma5=1590.5,
                ma20=1620.8,
                volume=5000000,
            ),
        ]

    def test_screen_stocks_no_conditions(self, mock_db, sample_stocks, sample_metrics):
        """测试无筛选条件的情况"""
        # 设置模拟
        mock_db.query.return_value.filter.return_value.all.return_value = sample_stocks
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.count.return_value = 3
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.limit.return_value.offset.return_value.all.return_value = [
            (sample_metrics[0], "平安银行"),
            (sample_metrics[1], "万科A"),
            (sample_metrics[2], "贵州茅台"),
        ]

        request = StockScreenerRequest(market="A_share", conditions=[], page=1, size=20)

        result = screen_stocks(mock_db, request)

        assert result.total == 3
        assert result.page == 1
        assert result.size == 20
        assert len(result.items) == 3
        assert result.items[0].code == "000001.SZ"
        assert result.items[0].name == "平安银行"
        assert result.items[0].pe_ratio == 15.2

    def test_screen_stocks_with_pe_filter(self, mock_db, sample_stocks, sample_metrics):
        """测试市盈率筛选"""
        # 创建完整的查询链模拟
        query_mock = Mock()
        subquery_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock1 = Mock()
        filter_mock2 = Mock()
        limit_mock = Mock()
        offset_mock = Mock()

        # 设置子查询链（latest_dates_subquery）
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock1
        filter_mock1.group_by.return_value = Mock()
        filter_mock1.group_by.return_value.subquery.return_value = subquery_mock

        # 重置 query mock 以便主查询使用
        mock_db.query.return_value = query_mock

        # 设置主查询链：query.join().join().filter()
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock2

        # 再次应用筛选条件后的查询链：filter().filter()
        filter_mock2.filter.return_value = filter_mock2  # 自引用以支持多次 filter

        # 重要：确保 count() 直接返回整数
        filter_mock2.count.return_value = 2

        # 设置分页链
        filter_mock2.limit.return_value = limit_mock
        limit_mock.offset.return_value = offset_mock

        # 修复：确保 all() 返回的是可迭代的列表
        offset_mock.all.return_value = [
            (sample_metrics[0], "平安银行"),
            (sample_metrics[1], "万科A"),
        ]

        request = StockScreenerRequest(
            market="A_share",
            conditions=[ScreenerCondition(field="pe_ratio", operator="lt", value=20.0)],
            page=1,
            size=20,
        )

        result = screen_stocks(mock_db, request)

        assert result.total == 2
        assert len(result.items) == 2
        # 验证筛选结果：PE < 20 的股票
        assert result.items[0].pe_ratio == 15.2  # 平安银行
        assert result.items[1].pe_ratio == 12.5  # 万科A

    def test_screen_stocks_with_market_cap_filter(
        self, mock_db, sample_stocks, sample_metrics
    ):
        """测试市值筛选"""
        # 创建完整的查询链模拟
        query_mock = Mock()
        subquery_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock1 = Mock()
        filter_mock2 = Mock()
        limit_mock = Mock()
        offset_mock = Mock()

        # 设置子查询链（latest_dates_subquery）
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock1
        filter_mock1.group_by.return_value = Mock()
        filter_mock1.group_by.return_value.subquery.return_value = subquery_mock

        # 重置 query mock 以便主查询使用
        mock_db.query.return_value = query_mock

        # 设置主查询链：query.join().join().filter()
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock2

        # 再次应用筛选条件后的查询链：filter().filter()
        filter_mock2.filter.return_value = filter_mock2  # 自引用以支持多次 filter

        # 重要：确保 count() 直接返回整数
        filter_mock2.count.return_value = 1

        # 设置分页链
        filter_mock2.limit.return_value = limit_mock
        limit_mock.offset.return_value = offset_mock

        # 修复：确保 all() 返回的是可迭代的列表
        offset_mock.all.return_value = [
            (sample_metrics[2], "贵州茅台"),
        ]

        request = StockScreenerRequest(
            market="A_share",
            conditions=[
                ScreenerCondition(
                    field="market_cap", operator="gt", value=1000000000000
                )  # > 1万亿
            ],
            page=1,
            size=20,
        )

        result = screen_stocks(mock_db, request)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].code == "600519.SH"
        assert result.items[0].name == "贵州茅台"
        assert result.items[0].market_cap == 1980000000000

    def test_screen_stocks_pagination(self, mock_db, sample_stocks, sample_metrics):
        """测试分页功能"""
        # 创建完整的查询链模拟
        query_mock = Mock()
        subquery_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock1 = Mock()
        filter_mock2 = Mock()
        limit_mock = Mock()
        offset_mock = Mock()

        # 设置子查询链（latest_dates_subquery）
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock1
        filter_mock1.group_by.return_value = Mock()
        filter_mock1.group_by.return_value.subquery.return_value = subquery_mock

        # 重置 query mock 以便主查询使用
        mock_db.query.return_value = query_mock

        # 设置主查询链：query.join().join().filter()
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock2

        # 重要：确保 count() 直接返回整数
        filter_mock2.count.return_value = 3

        # 设置分页链
        filter_mock2.limit.return_value = limit_mock
        limit_mock.offset.return_value = offset_mock

        # 修复：确保 all() 返回的是可迭代的列表
        offset_mock.all.return_value = [
            (sample_metrics[0], "平安银行"),
        ]

        request = StockScreenerRequest(
            market="A_share",
            conditions=[],
            page=1,
            size=1,  # 每页1条
        )

        result = screen_stocks(mock_db, request)

        assert result.total == 3
        assert result.page == 1
        assert result.size == 1
        assert len(result.items) == 1

    def test_screen_stocks_multiple_conditions(
        self, mock_db, sample_stocks, sample_metrics
    ):
        """测试多个筛选条件"""
        # 创建完整的查询链模拟
        query_mock = Mock()
        subquery_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock1 = Mock()
        filter_mock2 = Mock()
        limit_mock = Mock()
        offset_mock = Mock()

        # 设置子查询链（latest_dates_subquery）
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock1
        filter_mock1.group_by.return_value = Mock()
        filter_mock1.group_by.return_value.subquery.return_value = subquery_mock

        # 重置 query mock 以便主查询使用
        mock_db.query.return_value = query_mock

        # 设置主查询链：query.join().join().filter()
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock2

        # 再次应用筛选条件后的查询链：filter().filter()
        filter_mock2.filter.return_value = filter_mock2  # 自引用以支持多次 filter

        # 重要：确保 count() 直接返回整数
        filter_mock2.count.return_value = 1

        # 设置分页链
        filter_mock2.limit.return_value = limit_mock
        limit_mock.offset.return_value = offset_mock

        # 修复：确保 all() 返回的是可迭代的列表
        offset_mock.all.return_value = [
            (sample_metrics[1], "万科A"),
        ]

        request = StockScreenerRequest(
            market="A_share",
            conditions=[
                ScreenerCondition(
                    field="pe_ratio", operator="lt", value=20.0
                ),  # PE < 20
                ScreenerCondition(
                    field="market_cap", operator="lt", value=1000000000000
                ),  # 市值 < 1万亿
            ],
            page=1,
            size=20,
        )

        result = screen_stocks(mock_db, request)

        assert result.total == 1
        assert len(result.items) == 1
        # 验证筛选结果：PE < 20 且 市值 < 1万亿 的股票
        assert result.items[0].code == "000002.SZ"
        assert result.items[0].name == "万科A"
        assert result.items[0].pe_ratio == 12.5
        assert result.items[0].market_cap == 200000000000


if __name__ == "__main__":
    pytest.main([__file__])
