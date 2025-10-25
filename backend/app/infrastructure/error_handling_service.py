from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError

from app.infrastructure.database.models import DataQualityLog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ErrorSeverity(Enum):
    """错误严重程度枚举"""

    CRITICAL = "critical"  # 系统级错误，需要立即处理
    HIGH = "high"  # 高优先级错误，影响核心功能
    MEDIUM = "medium"  # 中等错误，影响部分功能
    LOW = "low"  # 低优先级错误，不影响主要功能
    INFO = "info"  # 信息性错误，仅作记录


class ErrorCategory(Enum):
    """错误分类枚举"""

    VALIDATION = "validation"  # 数据校验错误
    DEDUPLICATION = "deduplication"  # 去重处理错误
    DATABASE = "database"  # 数据库操作错误
    NETWORK = "network"  # 网络连接错误
    BUSINESS = "business"  # 业务逻辑错误
    SYSTEM = "system"  # 系统级错误
    EXTERNAL_API = "external_api"  # 外部API错误


@dataclass
class ErrorContext:
    """错误上下文信息"""

    operation: str  # 操作名称
    record_id: int | None = None
    table_name: str | None = None
    user_id: int | None = None
    request_id: str | None = None
    additional_data: dict[str, Any] | None = None


@dataclass
class ErrorDetail:
    """错误详情数据类"""

    error_code: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    timestamp: datetime
    stack_trace: str | None = None
    suggested_action: str | None = None
    recovery_steps: list[str] | None = None


@dataclass
class ErrorResponse:
    """错误响应数据类"""

    success: bool = False
    error_code: str = ""
    error_message: str = ""
    user_message: str = ""  # 用户友好的错误信息
    details: dict[str, Any] | None = None
    timestamp: datetime | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        """Post-initialize default timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class DataQualityError(Exception):
    """数据质量相关异常基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "DQ_ERROR",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.VALIDATION,
        context: ErrorContext | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext(operation="unknown")
        self.timestamp = datetime.now(timezone.utc)


class ValidationError(DataQualityError):
    """数据校验异常"""

    def __init__(
        self, message: str, field_name: str = "", invalid_value: Any = None, **kwargs
    ):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            **kwargs,
        )
        self.field_name = field_name
        self.invalid_value = invalid_value


class DeduplicationError(DataQualityError):
    """去重处理异常"""

    def __init__(self, message: str, duplicate_count: int = 0, **kwargs):
        super().__init__(
            message,
            error_code="DEDUPLICATION_ERROR",
            category=ErrorCategory.DEDUPLICATION,
            **kwargs,
        )
        self.duplicate_count = duplicate_count


class DatabaseError(DataQualityError):
    """数据库操作异常"""

    def __init__(self, message: str, sql_error: Exception | None = None, **kwargs):
        super().__init__(
            message,
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )
        self.sql_error = sql_error


class ErrorHandlingService:
    """错误处理服务类"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

        # 错误代码映射
        self.error_code_mapping = {
            # 校验错误
            "REQUIRED_FIELD_MISSING": "必填字段缺失",
            "INVALID_CODE_TYPE": "股票代码类型错误",
            "INVALID_CODE_FORMAT": "股票代码格式错误",
            "INVALID_DATE_FORMAT": "日期格式错误",
            "INVALID_DATE_TYPE": "日期类型错误",
            "INVALID_PRICE_TYPE": "价格类型错误",
            "PRICE_TOO_LOW": "价格过低",
            "PRICE_TOO_HIGH": "价格过高",
            "INVALID_HIGH_PRICE": "最高价逻辑错误",
            "INVALID_LOW_PRICE": "最低价逻辑错误",
            "INVALID_VOLUME_TYPE": "成交量类型错误",
            "NEGATIVE_VOLUME": "成交量不能为负",
            "VOLUME_TOO_HIGH": "成交量异常过大",
            "INVALID_PCT_CHG_TYPE": "涨跌幅类型错误",
            "ABNORMAL_CHANGE_PERCENT": "涨跌幅异常",
            # 去重错误
            "DUPLICATE_RECORD_FOUND": "发现重复记录",
            "DEDUPLICATION_FAILED": "去重处理失败",
            "SIMILARITY_CALCULATION_ERROR": "相似度计算错误",
            # 数据库错误
            "DB_CONNECTION_ERROR": "数据库连接错误",
            "DB_INTEGRITY_ERROR": "数据完整性约束错误",
            "DB_DATA_ERROR": "数据库数据错误",
            "DB_TRANSACTION_ERROR": "数据库事务错误",
            # 系统错误
            "SYSTEM_ERROR": "系统内部错误",
            "MEMORY_ERROR": "内存不足",
            "TIMEOUT_ERROR": "操作超时",
            "PERMISSION_ERROR": "权限不足",
        }

        # 用户友好错误信息映射
        self.user_friendly_messages = {
            "REQUIRED_FIELD_MISSING": "请检查必填字段是否完整",
            "INVALID_CODE_FORMAT": "请输入正确格式的股票代码",
            "INVALID_DATE_FORMAT": "请使用正确的日期格式 (YYYY-MM-DD)",
            "PRICE_TOO_LOW": "价格不能小于0.01元",
            "PRICE_TOO_HIGH": "价格超出合理范围",
            "NEGATIVE_VOLUME": "成交量不能为负数",
            "DB_CONNECTION_ERROR": "数据库连接异常，请稍后重试",
            "SYSTEM_ERROR": "系统繁忙，请稍后重试",
        }

    def handle_exception(
        self, exception: Exception, context: ErrorContext, log_to_db: bool = True
    ) -> ErrorResponse:
        """统一异常处理入口

        Args:
            exception: 异常对象
            context: 错误上下文
            log_to_db: 是否记录到数据库

        Returns:
            ErrorResponse: 错误响应
        """
        try:
            # 解析异常类型和详情
            error_detail = self._parse_exception(exception, context)

            # 记录错误日志
            self._log_error(error_detail)

            # 记录到数据库
            if log_to_db:
                self._log_to_database(error_detail)

            # 构建错误响应
            return self._build_error_response(error_detail)

        except Exception as e:
            # 处理异常处理过程中的异常
            self.logger.critical(f"错误处理服务异常: {e!s}")
            return self._build_fallback_error_response()

    def handle_validation_error(
        self,
        field_name: str,
        error_code: str,
        invalid_value: Any = None,
        context: ErrorContext | None = None,
    ) -> ErrorResponse:
        """处理数据校验错误

        Args:
            field_name: 字段名
            error_code: 错误代码
            invalid_value: 无效值
            context: 错误上下文

        Returns:
            ErrorResponse: 错误响应
        """
        error_message = self.error_code_mapping.get(error_code, "数据校验失败")

        validation_error = ValidationError(
            message=f"{field_name}: {error_message}",
            field_name=field_name,
            invalid_value=invalid_value,
            context=context or ErrorContext(operation="validation"),
        )
        validation_error.error_code = error_code

        return self.handle_exception(validation_error, validation_error.context)

    def handle_database_error(
        self,
        sql_error: SQLAlchemyError,
        operation: str,
        context: ErrorContext | None = None,
    ) -> ErrorResponse:
        """处理数据库错误

        Args:
            sql_error: SQLAlchemy异常
            operation: 操作名称
            context: 错误上下文

        Returns:
            ErrorResponse: 错误响应
        """
        error_code = self._classify_database_error(sql_error)
        error_message = self.error_code_mapping.get(error_code, "数据库操作失败")

        db_error = DatabaseError(
            message=f"{operation}: {error_message}",
            sql_error=sql_error,
            context=context or ErrorContext(operation=operation),
        )
        db_error.error_code = error_code

        return self.handle_exception(db_error, db_error.context, log_to_db=False)

    def _parse_exception(
        self, exception: Exception, context: ErrorContext
    ) -> ErrorDetail:
        """解析异常信息"""
        if isinstance(exception, DataQualityError):
            return ErrorDetail(
                error_code=exception.error_code,
                error_message=exception.message,
                severity=exception.severity,
                category=exception.category,
                context=exception.context,
                timestamp=exception.timestamp,
                stack_trace=traceback.format_exc(),
                suggested_action=self._get_suggested_action(exception.error_code),
                recovery_steps=self._get_recovery_steps(exception.error_code),
            )

        elif isinstance(exception, SQLAlchemyError):
            error_code = self._classify_database_error(exception)
            return ErrorDetail(
                error_code=error_code,
                error_message=str(exception),
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.DATABASE,
                context=context,
                timestamp=datetime.now(timezone.utc),
                stack_trace=traceback.format_exc(),
                suggested_action=self._get_suggested_action(error_code),
            )

        else:
            # 通用异常处理
            return ErrorDetail(
                error_code="SYSTEM_ERROR",
                error_message=str(exception),
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.SYSTEM,
                context=context,
                timestamp=datetime.now(timezone.utc),
                stack_trace=traceback.format_exc(),
                suggested_action="请联系系统管理员",
            )

    def _classify_database_error(self, sql_error: SQLAlchemyError) -> str:
        """分类数据库错误"""
        if isinstance(sql_error, IntegrityError):
            return "DB_INTEGRITY_ERROR"
        elif isinstance(sql_error, DataError):
            return "DB_DATA_ERROR"
        elif "connection" in str(sql_error).lower():
            return "DB_CONNECTION_ERROR"
        elif "timeout" in str(sql_error).lower():
            return "TIMEOUT_ERROR"
        else:
            return "DB_TRANSACTION_ERROR"

    def _get_suggested_action(self, error_code: str) -> str:
        """获取建议操作"""
        suggestions = {
            "REQUIRED_FIELD_MISSING": "请补充必填字段后重试",
            "INVALID_CODE_FORMAT": "请检查股票代码格式是否正确",
            "INVALID_DATE_FORMAT": "请使用 YYYY-MM-DD 格式的日期",
            "PRICE_TOO_LOW": "请检查价格数据是否正确",
            "PRICE_TOO_HIGH": "请确认价格数据的准确性",
            "DB_CONNECTION_ERROR": "请检查数据库连接状态",
            "DB_INTEGRITY_ERROR": "请检查数据完整性约束",
            "SYSTEM_ERROR": "请联系技术支持",
        }
        return suggestions.get(error_code, "请检查输入数据并重试")

    def _get_recovery_steps(self, error_code: str) -> list[str]:
        """获取恢复步骤"""
        recovery_steps = {
            "VALIDATION_ERROR": [
                "1. 检查数据格式是否正确",
                "2. 确认必填字段已填写",
                "3. 验证数据范围是否合理",
            ],
            "DB_CONNECTION_ERROR": [
                "1. 检查网络连接",
                "2. 确认数据库服务状态",
                "3. 重试操作",
                "4. 联系系统管理员",
            ],
            "DEDUPLICATION_ERROR": [
                "1. 检查重复数据的来源",
                "2. 确认去重策略设置",
                "3. 手动处理冲突数据",
            ],
        }
        return recovery_steps.get(error_code, ["请联系技术支持获取帮助"])

    def _log_error(self, error_detail: ErrorDetail) -> None:
        """记录错误日志"""
        log_level = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.INFO: logging.INFO,
        }.get(error_detail.severity, logging.ERROR)

        log_message = (
            f"[{error_detail.category.value.upper()}] "
            f"{error_detail.error_code}: {error_detail.error_message}"
        )

        extra_info = {
            "error_code": error_detail.error_code,
            "category": error_detail.category.value,
            "severity": error_detail.severity.value,
            "operation": error_detail.context.operation,
            "record_id": error_detail.context.record_id,
            "table_name": error_detail.context.table_name,
        }

        self.logger.log(log_level, log_message, extra=extra_info)

    def _log_to_database(self, error_detail: ErrorDetail) -> None:
        """记录错误到数据库"""
        try:
            log_entry = DataQualityLog(
                record_id=error_detail.context.record_id,
                table_name=error_detail.context.table_name or "unknown",
                operation_type="error_handling",
                status="error",
                message=f"[{error_detail.error_code}] {error_detail.error_message}",
                error_details=json.dumps(
                    {
                        "error_code": error_detail.error_code,
                        "severity": error_detail.severity.value,
                        "category": error_detail.category.value,
                        "suggested_action": error_detail.suggested_action,
                        "stack_trace": (
                            error_detail.stack_trace[:1000]
                            if error_detail.stack_trace
                            else None
                        ),
                    },
                    ensure_ascii=False,
                ),
                execution_time=0.0,
            )

            self.db_session.add(log_entry)
            self.db_session.commit()

        except Exception:
            self.logger.exception("记录错误日志到数据库失败")
            self.db_session.rollback()

    def _build_error_response(self, error_detail: ErrorDetail) -> ErrorResponse:
        """构建错误响应"""
        user_message = self.user_friendly_messages.get(
            error_detail.error_code, "操作失败，请检查输入数据"
        )

        return ErrorResponse(
            success=False,
            error_code=error_detail.error_code,
            error_message=error_detail.error_message,
            user_message=user_message,
            details={
                "severity": error_detail.severity.value,
                "category": error_detail.category.value,
                "suggested_action": error_detail.suggested_action,
                "recovery_steps": error_detail.recovery_steps,
            },
            timestamp=error_detail.timestamp,
            request_id=error_detail.context.request_id,
        )

    def _build_fallback_error_response(self) -> ErrorResponse:
        """构建备用错误响应"""
        return ErrorResponse(
            success=False,
            error_code="SYSTEM_ERROR",
            error_message="系统内部错误",
            user_message="系统繁忙，请稍后重试",
            timestamp=datetime.now(timezone.utc),
        )

    def create_success_response(
        self, data: Any = None, message: str = "操作成功"
    ) -> dict[str, Any]:
        """创建成功响应"""
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
