import unittest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.data_validation_service import (
    DataValidationService,
    ValidationRule,
    ValidationResult,
    ValidationReport,
    ValidationSeverity,
)


class TestDataValidationService(unittest.TestCase):
    """数据校验服务测试类"""

    def setUp(self):
        """测试前置设置"""
        # 创建内存数据库用于测试
        self.engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=self.engine)
        self.session = SessionLocal()

        # 创建模拟的数据库会话
        self.mock_session = Mock(spec=Session)

        # 初始化服务
        self.validation_service = DataValidationService(self.mock_session)

        # 测试数据
        self.valid_stock_data = {
            "code": "000001",
            "date": "2024-01-15",
            "open": 10.50,
            "close": 10.80,
            "high": 11.00,
            "low": 10.30,
            "volume": 1000000,
            "turnover": 10800000.0,
            "pe_ratio": 15.5,
            "market_cap": 108000000000.0,
        }

        self.invalid_stock_data = {
            "code": "",  # 无效股票代码
            "date": "2024-13-45",  # 无效日期
            "open": -10.50,  # 负价格
            "close": "invalid",  # 非数字
            "high": 5.00,  # 最高价小于最低价
            "low": 15.00,
            "volume": -1000,  # 负成交量
            "turnover": None,  # 空值
            "pe_ratio": "N/A",  # 非数字
            "market_cap": float("inf"),  # 无穷大
        }

    def tearDown(self):
        """测试后清理"""
        self.session.close()

    def test_validate_stock_code_valid(self):
        """测试有效股票代码校验"""
        # A股代码
        result = self.validation_service._validate_stock_code("000001", "A_share")
        self.assertTrue(result.is_valid)

        # 港股代码
        result = self.validation_service._validate_stock_code("00700", "HK_share")
        self.assertTrue(result.is_valid)

        # 美股代码
        result = self.validation_service._validate_stock_code("AAPL", "US_share")
        self.assertTrue(result.is_valid)

    def test_validate_stock_code_invalid(self):
        """测试无效股票代码校验"""
        # 空代码
        result = self.validation_service._validate_stock_code("", "A_share")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)

        # 格式错误
        result = self.validation_service._validate_stock_code("ABC123", "A_share")
        self.assertFalse(result.is_valid)

        # 长度错误
        result = self.validation_service._validate_stock_code("1234567", "A_share")
        self.assertFalse(result.is_valid)

    def test_validate_date_valid(self):
        """测试有效日期校验"""
        # 字符串日期
        result = self.validation_service._validate_date("2024-01-15")
        self.assertTrue(result.is_valid)

        # datetime对象
        result = self.validation_service._validate_date(datetime(2024, 1, 15))
        self.assertTrue(result.is_valid)

        # date对象
        result = self.validation_service._validate_date(date(2024, 1, 15))
        self.assertTrue(result.is_valid)

    def test_validate_date_invalid(self):
        """测试无效日期校验"""
        # 无效日期格式
        result = self.validation_service._validate_date("2024-13-45")
        self.assertFalse(result.is_valid)

        # 空值
        result = self.validation_service._validate_date(None)
        self.assertFalse(result.is_valid)

        # 未来日期测试（根据实际业务逻辑调整）
        # future_date = datetime.now().strftime("%Y-%m-%d")
        # TODO: 添加未来日期的具体测试逻辑

    def test_validate_price_valid(self):
        """测试有效价格校验"""
        # 正常价格
        result = self.validation_service._validate_price(10.50, "open_price")
        self.assertTrue(result.is_valid)

        # Decimal类型
        result = self.validation_service._validate_price(
            Decimal("10.50"), "close_price"
        )
        self.assertTrue(result.is_valid)

        # 零价格应该无效（低于最小价格限制0.01）
        result = self.validation_service._validate_price(0.0, "low_price")
        self.assertFalse(result.is_valid)

    def test_validate_price_invalid(self):
        """测试无效价格校验"""
        # 负价格
        result = self.validation_service._validate_price(-10.50, "open_price")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)

        # 非数字
        result = self.validation_service._validate_price("invalid", "close_price")
        self.assertFalse(result.is_valid)

        # 无穷大
        result = self.validation_service._validate_price(float("inf"), "high_price")
        self.assertFalse(result.is_valid)

        # NaN
        result = self.validation_service._validate_price(float("nan"), "low_price")
        self.assertFalse(result.is_valid)

    def test_validate_volume_valid(self):
        """测试有效成交量校验"""
        # 正常成交量
        result = self.validation_service._validate_volume(1000000)
        self.assertTrue(result.is_valid)

        # 零成交量
        result = self.validation_service._validate_volume(0)
        self.assertTrue(result.is_valid)  # 可能在某些情况下有效

    def test_validate_volume_invalid(self):
        """测试无效成交量校验"""
        # 负成交量
        result = self.validation_service._validate_volume(-1000)
        self.assertFalse(result.is_valid)

        # 非整数
        result = self.validation_service._validate_volume(1000.5)
        self.assertFalse(result.is_valid)

        # 非数字
        result = self.validation_service._validate_volume("invalid")
        self.assertFalse(result.is_valid)

    def test_validate_price_relationships_valid(self):
        """测试有效价格关系校验"""
        data = {"open": 10.50, "close": 10.80, "high": 11.00, "low": 10.30}

        result = self.validation_service._validate_price_relationships(data)
        self.assertTrue(result.is_valid)

    def test_validate_price_relationships_invalid(self):
        """测试无效价格关系校验"""
        # 最高价小于最低价
        data = {
            "open": 10.50,
            "close": 10.80,
            "high": 10.00,  # 最高价小于开盘价
            "low": 10.30,
        }

        result = self.validation_service._validate_price_relationships(data)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)

    def test_validate_change_percent_valid(self):
        """测试有效涨跌幅校验"""
        # 正常涨跌幅
        result = self.validation_service._validate_change_percent(5.5, "A_share")
        self.assertTrue(result.is_valid)

        # 边界值
        result = self.validation_service._validate_change_percent(10.0, "A_share")
        self.assertTrue(result.is_valid)

        result = self.validation_service._validate_change_percent(-10.0, "A_share")
        self.assertTrue(result.is_valid)

    def test_validate_change_percent_invalid(self):
        """测试无效涨跌幅校验"""
        # 超出A股涨跌停限制
        result = self.validation_service._validate_change_percent(15.0, "A_share")
        self.assertFalse(result.is_valid)
        self.assertEqual(
            result.severity, ValidationSeverity.WARNING
        )  # 可能是警告而非错误

        result = self.validation_service._validate_change_percent(-15.0, "A_share")
        self.assertFalse(result.is_valid)

    def test_validate_stock_data_complete_valid(self):
        """测试完整有效数据校验"""
        report = self.validation_service.validate_stock_data(
            self.valid_stock_data, "A_share"
        )

        self.assertIsInstance(report, ValidationReport)
        self.assertTrue(report.is_valid)
        self.assertGreater(report.quality_score, 0.8)  # 高质量分数
        self.assertEqual(len(report.errors), 0)

    def test_validate_stock_data_complete_invalid(self):
        """测试完整无效数据校验"""
        report = self.validation_service.validate_stock_data(
            self.invalid_stock_data, "A_share"
        )

        self.assertIsInstance(report, ValidationReport)
        self.assertFalse(report.is_valid)
        self.assertLess(report.quality_score, 0.5)  # 低质量分数
        self.assertGreater(len(report.errors), 0)

    def test_calculate_quality_score(self):
        """测试质量分数计算"""
        # 无错误无警告
        is_valid, score = self.validation_service._calculate_quality_score([])
        self.assertEqual(score, 1.0)
        self.assertTrue(is_valid)

        # 有警告无错误
        warnings = [
            ValidationResult(
                True, "test", "warning", ValidationSeverity.WARNING, "WARN_001"
            )
        ]
        is_valid, score = self.validation_service._calculate_quality_score(warnings)
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.5)
        self.assertTrue(is_valid)

        # 有错误
        errors = [
            ValidationResult(
                False, "test", "error", ValidationSeverity.ERROR, "ERR_001"
            )
        ]
        is_valid, score = self.validation_service._calculate_quality_score(errors)
        self.assertLess(score, 1.0)
        self.assertFalse(is_valid)

    @patch("app.services.data_validation_service.DataQualityLog")
    def test_log_validation_result(self, mock_log_class):
        """测试校验结果日志记录"""
        mock_log_instance = Mock()
        mock_log_class.return_value = mock_log_instance

        report = ValidationReport(
            record_id="test_id",
            is_valid=True,
            quality_score=0.95,
            results=[],
            execution_time=0.1,
            errors=[],
            warnings=[],
            validation_time=0.1,
            validated_at=datetime.now(),
        )

        self.validation_service.log_validation_result(1, "daily_stock_metrics", report)

        # 验证日志对象被创建
        mock_log_class.assert_called_once()

        # 验证会话操作
        self.mock_session.add.assert_called_once_with(mock_log_instance)
        self.mock_session.commit.assert_called_once()

    def test_batch_validate_data(self):
        """测试批量数据校验"""
        data_list = [self.valid_stock_data, self.invalid_stock_data]

        reports = self.validation_service.batch_validate_data(data_list, "A_share")

        self.assertEqual(len(reports), 2)
        self.assertIsInstance(reports[0], ValidationReport)
        self.assertIsInstance(reports[1], ValidationReport)

        # 第一个应该有效，第二个无效
        self.assertTrue(reports[0].is_valid)
        self.assertFalse(reports[1].is_valid)

    def test_get_validation_rules(self):
        """测试获取校验规则"""
        rules = self.validation_service.get_validation_rules("A_share")

        self.assertIsInstance(rules, list)
        self.assertGreater(len(rules), 0)

        # 检查规则结构
        for rule in rules:
            self.assertIsInstance(rule, ValidationRule)
            self.assertIsNotNone(rule.field_name)
            self.assertIsNotNone(rule.rule_type)

    def test_edge_cases(self):
        """测试边界情况"""
        # 空数据
        report = self.validation_service.validate_stock_data({}, "A_share")
        self.assertFalse(report.is_valid)

        # None数据
        report = self.validation_service.validate_stock_data(None, "A_share")
        self.assertFalse(report.is_valid)

        # 不支持的市场类型
        report = self.validation_service.validate_stock_data(
            self.valid_stock_data, "UNKNOWN"
        )
        # 应该使用默认规则或返回错误

    def test_performance_with_large_dataset(self):
        """测试大数据集性能"""
        # 创建大量测试数据
        large_dataset = [self.valid_stock_data.copy() for _ in range(1000)]

        start_time = datetime.now()
        reports = self.validation_service.batch_validate_data(large_dataset, "A_share")
        end_time = datetime.now()

        processing_time = (end_time - start_time).total_seconds()

        # 验证结果
        self.assertEqual(len(reports), 1000)

        # 性能要求：1000条记录应在合理时间内完成
        self.assertLess(processing_time, 10.0)  # 10秒内完成

        # 验证处理速度
        processing_rate = len(reports) / processing_time
        self.assertGreater(processing_rate, 100)  # 每秒至少处理100条


if __name__ == "__main__":
    unittest.main()