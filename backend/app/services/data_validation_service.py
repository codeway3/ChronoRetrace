import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import DataQualityLog


class ValidationCategory(Enum):
    """数据校验类别枚举"""

    DATA_TYPE = "data_type"
    RANGE = "range"
    FORMAT = "format"
    BUSINESS_RULE = "business_rule"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"


class ValidationStatus(Enum):
    """校验状态枚举"""

    PENDING = "pending"
    VALIDATED = "validated"
    FAILED = "failed"


class ValidationSeverity(Enum):
    """校验严重程度"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationRule:
    """校验规则数据类"""

    field_name: str
    rule_type: str  # 'format', 'range', 'type', 'logic'
    rule_config: Dict[str, Any] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    error_message: str = ""
    is_enabled: bool = True


@dataclass
class ValidationResult:
    """校验结果数据类"""

    is_valid: bool
    field_name: str
    message: str
    severity: ValidationSeverity
    suggested_value: Optional[Any] = None
    error_code: Optional[str] = None


@dataclass
class ValidationReport:
    """校验报告数据类"""

    is_valid: bool
    quality_score: float  # 0.0 - 1.0
    results: List[ValidationResult]
    execution_time: float
    validated_at: datetime
    record_id: Optional[str] = None
    validation_time: Optional[float] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = [
                r.message
                for r in self.results
                if r.severity == ValidationSeverity.ERROR and not r.is_valid
            ]
        if self.warnings is None:
            self.warnings = [
                r.message
                for r in self.results
                if r.severity == ValidationSeverity.WARNING
            ]
        # 如果没有提供validation_time，使用execution_time
        if self.validation_time is None:
            self.validation_time = self.execution_time


class DataValidationService:
    """数据校验服务类"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

        # 股票代码格式规则
        self.stock_code_patterns = {
            "A_share": re.compile(r"^[0-9]{6}$"),  # 6位数字
            "US_stock": re.compile(r"^[A-Z]{1,5}$"),  # 1-5位大写字母
            "HK_stock": re.compile(r"^[0-9]{5}$"),  # 5位数字
        }

        # 价格范围限制
        self.price_limits = {
            "min_price": 0.01,
            "max_price": 10000.0,
            "max_change_percent": 10.0,  # 单日最大涨跌幅（A股涨跌停限制）
        }

        # 成交量范围限制
        self.volume_limits = {
            "min_volume": 0,
            "max_volume": 1e12,  # 1万亿
        }

    def validate_stock_data(
        self, data: Dict[str, Any], market_type: str = "A_share"
    ) -> ValidationReport:
        """校验股票数据

        Args:
            data: 股票数据字典
            market_type: 市场类型 (A_share, US_stock, HK_stock)

        Returns:
            ValidationReport: 校验报告
        """
        start_time = datetime.now()
        results = []

        # 检查数据是否为None
        if data is None:
            data = {}

        # 必填字段校验
        required_fields = ["code", "date", "close"]
        for field in required_fields:
            result = self._validate_required_field(data, field)
            if result:
                results.append(result)

        # 股票代码格式校验
        if "code" in data:
            result = self._validate_stock_code(data["code"], market_type)
            if result:
                results.append(result)

        # 日期格式校验
        if "date" in data:
            result = self._validate_date(data["date"])
            if result:
                results.append(result)

        # 价格数据校验
        price_fields = ["open", "high", "low", "close", "pre_close"]
        for field in price_fields:
            if field in data:
                result = self._validate_price(data[field], field)
                if result:
                    results.append(result)

        # 价格逻辑关系校验
        if all(field in data for field in ["open", "high", "low", "close"]):
            logic_results = self._validate_price_logic(data)
            results.extend(logic_results)

        # 成交量校验
        if "volume" in data:
            result = self._validate_volume(data["volume"])
            results.append(result)

        # 涨跌幅校验
        if "pct_chg" in data:
            result = self._validate_change_percent(data["pct_chg"], market_type)
            results.append(result)

        # 计算质量评分和整体有效性
        is_valid, quality_score = self._calculate_quality_score(results)

        execution_time = (datetime.now() - start_time).total_seconds()

        return ValidationReport(
            is_valid=is_valid,
            quality_score=quality_score,
            results=results,
            execution_time=execution_time,
            validated_at=datetime.now(),
        )

    def _validate_required_field(
        self, data: Dict[str, Any], field_name: str
    ) -> Optional[ValidationResult]:
        """校验必填字段"""
        if data is None or field_name not in data or data[field_name] is None:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"必填字段 '{field_name}' 缺失",
                severity=ValidationSeverity.ERROR,
                error_code="REQUIRED_FIELD_MISSING",
            )
        return None

    def _validate_stock_code(self, code: str, market_type: str) -> ValidationResult:
        """校验股票代码格式"""
        if not isinstance(code, str):
            return ValidationResult(
                is_valid=False,
                field_name="code",
                message="股票代码必须是字符串类型",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_CODE_TYPE",
            )

        pattern = self.stock_code_patterns.get(market_type)
        if pattern and not pattern.match(code):
            return ValidationResult(
                is_valid=False,
                field_name="code",
                message=f"股票代码格式不符合 {market_type} 市场规范",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_CODE_FORMAT",
            )

        # 验证成功时返回有效的ValidationResult
        return ValidationResult(
            is_valid=True,
            field_name="code",
            message="股票代码格式正确",
            severity=ValidationSeverity.INFO,
            error_code="VALID_CODE",
        )

    def _validate_date(self, date_value: Any) -> ValidationResult:
        """校验日期格式"""
        if date_value is None:
            return ValidationResult(
                is_valid=False,
                field_name="date",
                message="日期不能为空",
                severity=ValidationSeverity.ERROR,
                error_code="DATE_NULL",
            )

        if isinstance(date_value, str):
            try:
                datetime.strptime(date_value, "%Y-%m-%d")
            except ValueError:
                return ValidationResult(
                    is_valid=False,
                    field_name="date",
                    message="日期格式错误，应为 YYYY-MM-DD",
                    severity=ValidationSeverity.ERROR,
                    error_code="INVALID_DATE_FORMAT",
                )
        elif not isinstance(date_value, (date, datetime)):
            return ValidationResult(
                is_valid=False,
                field_name="date",
                message="日期类型错误",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_DATE_TYPE",
            )

        # 验证成功时返回有效的ValidationResult
        return ValidationResult(
            is_valid=True,
            field_name="date",
            message="日期格式正确",
            severity=ValidationSeverity.INFO,
            error_code="VALID_DATE",
        )

    def _validate_price(self, price: Any, field_name: str) -> ValidationResult:
        """校验价格数据"""
        if price is None:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"价格 '{field_name}' 不能为空",
                severity=ValidationSeverity.ERROR,
                error_code="PRICE_NULL",
            )

        try:
            price_float = float(price)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"价格 '{field_name}' 必须是数字类型",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_PRICE_TYPE",
            )

        # 检查无穷大和NaN值
        import math

        if math.isinf(price_float):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"价格 '{field_name}' 不能是无穷大",
                severity=ValidationSeverity.ERROR,
                error_code="PRICE_INFINITE",
            )

        if math.isnan(price_float):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"价格 '{field_name}' 不能是NaN",
                severity=ValidationSeverity.ERROR,
                error_code="PRICE_NAN",
            )

        if price_float < self.price_limits["min_price"]:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"价格 '{field_name}' 不能小于 {self.price_limits['min_price']}",
                severity=ValidationSeverity.ERROR,
                error_code="PRICE_TOO_LOW",
            )

        if price_float > self.price_limits["max_price"]:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"价格 '{field_name}' 不能大于 {self.price_limits['max_price']}",
                severity=ValidationSeverity.ERROR,
                error_code="PRICE_TOO_HIGH",
            )

        # 验证成功时返回有效的ValidationResult
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            message=f"价格 '{field_name}' 格式正确",
            severity=ValidationSeverity.INFO,
            error_code="VALID_PRICE",
        )

    def _validate_price_logic(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """校验价格逻辑关系"""
        results = []

        # 验证价格数据是否可以转换为浮点数
        try:
            float(data["open"])
            float(data["high"])
            float(data["low"])
            float(data["close"])
        except (ValueError, TypeError):
            return results

        # 添加价格关系验证
        price_relationship_result = self._validate_price_relationships(data)
        if price_relationship_result:
            results.append(price_relationship_result)

        return results

    def _validate_price_relationships(self, data: Dict[str, Any]) -> ValidationResult:
        """校验价格关系逻辑"""
        try:
            open_price = float(data.get("open", 0))
            high_price = float(data.get("high", 0))
            low_price = float(data.get("low", 0))
            close_price = float(data.get("close", 0))
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name="price_relationships",
                message="价格数据类型错误，无法进行关系校验",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_PRICE_TYPE_FOR_RELATIONSHIP",
            )

        # 检查最高价是否是最高的
        if high_price < max(open_price, close_price, low_price):
            return ValidationResult(
                is_valid=False,
                field_name="high",
                message="最高价应该大于等于开盘价、收盘价和最低价",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_HIGH_PRICE",
            )

        # 检查最低价是否是最低的
        if low_price > min(open_price, close_price, high_price):
            return ValidationResult(
                is_valid=False,
                field_name="low",
                message="最低价应该小于等于开盘价、收盘价和最高价",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_LOW_PRICE",
            )

        # 验证成功
        return ValidationResult(
            is_valid=True,
            field_name="price_relationships",
            message="价格关系逻辑正确",
            severity=ValidationSeverity.INFO,
            error_code="VALID_PRICE_RELATIONSHIPS",
        )

    def _validate_volume(self, volume: Any) -> ValidationResult:
        """校验成交量数据"""
        if volume is None:
            return ValidationResult(
                is_valid=False,
                field_name="volume",
                message="成交量不能为空",
                severity=ValidationSeverity.ERROR,
                error_code="VOLUME_NULL",
            )

        try:
            volume_float = float(volume)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name="volume",
                message="成交量必须是数字类型",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_VOLUME_TYPE",
            )

        if volume_float < 0:
            return ValidationResult(
                is_valid=False,
                field_name="volume",
                message="成交量不能为负数",
                severity=ValidationSeverity.ERROR,
                error_code="NEGATIVE_VOLUME",
            )

        # 检查是否为整数（成交量通常应该是整数）
        if volume_float != int(volume_float):
            return ValidationResult(
                is_valid=False,
                field_name="volume",
                message="成交量应该是整数",
                severity=ValidationSeverity.ERROR,
                error_code="NON_INTEGER_VOLUME",
            )

        # 验证成功
        return ValidationResult(
            is_valid=True,
            field_name="volume",
            message="成交量格式正确",
            severity=ValidationSeverity.INFO,
            error_code="VALID_VOLUME",
        )

    def _validate_change_percent(
        self, pct_chg: Any, market_type: str = "A_share"
    ) -> ValidationResult:
        """校验涨跌幅"""
        if pct_chg is None:
            return ValidationResult(
                is_valid=False,
                field_name="pct_chg",
                message="涨跌幅不能为空",
                severity=ValidationSeverity.ERROR,
                error_code="PCT_CHG_NULL",
            )

        try:
            pct_float = float(pct_chg)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name="pct_chg",
                message="涨跌幅必须是数字类型",
                severity=ValidationSeverity.ERROR,
                error_code="INVALID_PCT_CHG_TYPE",
            )

        if abs(pct_float) > self.price_limits["max_change_percent"]:
            return ValidationResult(
                is_valid=False,
                field_name="pct_chg",
                message=f"涨跌幅异常: {pct_float}%，超过限制 {self.price_limits['max_change_percent']}%",
                severity=ValidationSeverity.WARNING,
                error_code="ABNORMAL_CHANGE_PERCENT",
            )

        # 验证成功
        return ValidationResult(
            is_valid=True,
            field_name="pct_chg",
            message="涨跌幅格式正确",
            severity=ValidationSeverity.INFO,
            error_code="VALID_PCT_CHG",
        )

    def _calculate_quality_score(
        self, results: List[ValidationResult]
    ) -> Tuple[bool, float]:
        """计算数据质量评分"""
        if not results:
            return True, 1.0

        error_count = sum(1 for r in results if r.severity == ValidationSeverity.ERROR)
        warning_count = sum(
            1 for r in results if r.severity == ValidationSeverity.WARNING
        )

        # 有错误则数据无效
        is_valid = error_count == 0

        # 计算质量评分 (错误-0.2分，警告-0.1分)
        total_deduction = error_count * 0.2 + warning_count * 0.1
        quality_score = max(0.0, 1.0 - total_deduction)

        return is_valid, quality_score

    def get_validation_rules(self, table_name: str = None) -> List[ValidationRule]:
        """获取所有验证规则"""
        rules = []

        # 股票代码规则
        rules.append(
            ValidationRule(
                field_name="code",
                rule_type="format",
                rule_config={"pattern": "^[0-9]{6}$"},
                severity=ValidationSeverity.ERROR,
                error_message="股票代码格式验证",
            )
        )

        # 价格规则
        for field in ["open", "high", "low", "close"]:
            rules.append(
                ValidationRule(
                    field_name=field,
                    rule_type="range",
                    rule_config={"min": 0.01, "max": 10000.0},
                    severity=ValidationSeverity.ERROR,
                    error_message=f"{field}价格范围验证",
                )
            )

        # 成交量规则
        rules.append(
            ValidationRule(
                field_name="volume",
                rule_type="range",
                rule_config={"min": 0},
                severity=ValidationSeverity.ERROR,
                error_message="成交量范围验证",
            )
        )

        return rules

    def log_validation_result(
        self, record_id: int, table_name: str, validation_report: ValidationReport
    ) -> None:
        """记录校验结果到数据库"""
        try:
            log_entry = DataQualityLog(
                record_id=record_id,
                table_name=table_name,
                operation_type="validation",
                status="success" if validation_report.is_valid else "failed",
                message=f"质量评分: {validation_report.quality_score:.2f}",
                error_details=self._format_validation_errors(validation_report.results),
                execution_time=validation_report.execution_time,
            )

            self.db_session.add(log_entry)
            self.db_session.commit()

        except Exception as e:
            self.logger.error(f"记录校验日志失败: {str(e)}")
            self.db_session.rollback()

    def _format_validation_errors(
        self, results: List[ValidationResult]
    ) -> Optional[str]:
        """格式化校验错误信息"""
        if not results:
            return None

        error_messages = []
        for result in results:
            if not result.is_valid:
                error_messages.append(f"{result.field_name}: {result.message}")

        return "; ".join(error_messages) if error_messages else None

    def batch_validate_data(
        self, data_list: List[Dict[str, Any]], data_type: str = "stock_data"
    ) -> List[ValidationReport]:
        """批量校验数据"""
        reports = []
        for data in data_list:
            report = self.validate_stock_data(data)
            reports.append(report)
        return reports