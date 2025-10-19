from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.infrastructure.database.models import DataQualityLog


class LogLevel(Enum):
    """日志级别枚举"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OperationType(Enum):
    """操作类型枚举"""

    VALIDATION = "validation"
    DEDUPLICATION = "deduplication"
    DATA_IMPORT = "data_import"
    DATA_EXPORT = "data_export"
    DATA_CLEANUP = "data_cleanup"
    BATCH_PROCESSING = "batch_processing"
    SYSTEM_MAINTENANCE = "system_maintenance"
    USER_ACTION = "user_action"
    PIPELINE = "pipeline"
    QUALITY_CHECK = "quality_check"


class LogStatus(Enum):
    """日志状态枚举"""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class LogEntry:
    """日志条目数据类"""

    operation_id: str
    operation_type: OperationType
    status: LogStatus
    level: LogLevel
    message: str
    timestamp: datetime
    record_id: int | None = None
    table_name: str | None = None
    user_id: int | None = None
    session_id: str | None = None
    execution_time: float | None = None
    details: dict[str, Any] | None = None
    error_details: str | None = None
    metrics: dict[str, int | float] | None = None


@dataclass
class OperationMetrics:
    """操作指标数据类"""

    total_records: int = 0
    processed_records: int = 0
    success_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    duplicates_found: int = 0
    duplicates_removed: int = 0
    validation_errors: int = 0
    warnings: int = 0
    execution_time: float = 0.0
    memory_usage: float | None = None
    cpu_usage: float | None = None


@dataclass
class BatchOperationLog:
    """批量操作日志数据类"""

    batch_id: str
    operation_type: OperationType
    start_time: datetime
    end_time: datetime | None = None
    status: LogStatus = LogStatus.STARTED
    metrics: OperationMetrics | None = None
    sub_operations: list[str] | None = None  # 子操作ID列表
    error_summary: str | None = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = OperationMetrics()
        if self.sub_operations is None:
            self.sub_operations = []


class LoggingService:
    """日志记录服务类"""

    def __init__(self, db_session: Session, log_file_path: str | None = None):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

        # 当前活跃的操作记录
        self.active_operations: dict[str, BatchOperationLog] = {}

        # 配置文件日志
        if log_file_path:
            self._setup_file_logging(log_file_path)

        # 日志保留策略
        self.retention_days = 30
        self.max_log_entries = 100000

    def _setup_file_logging(self, log_file_path: str) -> None:
        """设置文件日志记录"""
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def start_operation(
        self,
        operation_type: OperationType,
        description: str = "",
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> str:
        """开始一个操作并返回操作ID

        Args:
            operation_type: 操作类型
            description: 操作描述
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            str: 操作ID
        """
        operation_id = str(uuid.uuid4())

        batch_log = BatchOperationLog(
            batch_id=operation_id,
            operation_type=operation_type,
            start_time=datetime.now(),
            status=LogStatus.STARTED,
        )

        self.active_operations[operation_id] = batch_log

        # 记录开始日志
        self.log_operation(
            operation_id=operation_id,
            operation_type=operation_type,
            status=LogStatus.STARTED,
            level=LogLevel.INFO,
            message=f"开始操作: {description or operation_type.value}",
            user_id=user_id,
            session_id=session_id,
        )

        return operation_id

    def log_operation(
        self,
        operation_id: str,
        operation_type: OperationType,
        status: LogStatus,
        level: LogLevel,
        message: str,
        record_id: int | None = None,
        table_name: str | None = None,
        user_id: int | None = None,
        session_id: str | None = None,
        execution_time: float | None = None,
        details: dict[str, Any] | None = None,
        error_details: str | None = None,
        metrics: dict[str, int | float] | None = None,
    ) -> None:
        """记录操作日志

        Args:
            operation_id: 操作ID
            operation_type: 操作类型
            status: 操作状态
            level: 日志级别
            message: 日志消息
            record_id: 记录ID
            table_name: 表名
            user_id: 用户ID
            session_id: 会话ID
            execution_time: 执行时间
            details: 详细信息
            error_details: 错误详情
            metrics: 指标数据
        """
        log_entry = LogEntry(
            operation_id=operation_id,
            operation_type=operation_type,
            status=status,
            level=level,
            message=message,
            timestamp=datetime.now(),
            record_id=record_id,
            table_name=table_name,
            user_id=user_id,
            session_id=session_id,
            execution_time=execution_time,
            details=details,
            error_details=error_details,
            metrics=metrics,
        )

        # 记录到文件日志
        self._log_to_file(log_entry)

        # 记录到数据库
        self._log_to_database(log_entry)

        # 更新批量操作状态
        if operation_id in self.active_operations:
            self._update_batch_operation(operation_id, log_entry)

    def log_validation_result(
        self,
        operation_id: str,
        record_id: int,
        table_name: str,
        is_valid: bool,
        quality_score: float,
        validation_errors: list[str] | None = None,
        execution_time: float = 0.0,
    ) -> None:
        """记录数据校验结果

        Args:
            operation_id: 操作ID
            record_id: 记录ID
            table_name: 表名
            is_valid: 是否有效
            quality_score: 质量评分
            validation_errors: 校验错误列表
            execution_time: 执行时间
        """
        status = LogStatus.SUCCESS if is_valid else LogStatus.FAILED
        level = LogLevel.INFO if is_valid else LogLevel.WARNING

        message = (
            f"数据校验{'成功' if is_valid else '失败'}, 质量评分: {quality_score:.2f}"
        )

        details = {
            "is_valid": is_valid,
            "quality_score": quality_score,
            "validation_errors": validation_errors or [],
        }

        metrics = {
            "quality_score": quality_score,
            "error_count": len(validation_errors) if validation_errors else 0,
        }

        self.log_operation(
            operation_id=operation_id,
            operation_type=OperationType.VALIDATION,
            status=status,
            level=level,
            message=message,
            record_id=record_id,
            table_name=table_name,
            execution_time=execution_time,
            details=details,
            error_details="; ".join(validation_errors) if validation_errors else None,
            metrics=metrics,
        )

    def log_deduplication_result(
        self,
        operation_id: str,
        table_name: str,
        total_processed: int,
        duplicates_found: int,
        duplicates_removed: int,
        execution_time: float = 0.0,
        strategy: str = "",
    ) -> None:
        """记录去重处理结果

        Args:
            operation_id: 操作ID
            table_name: 表名
            total_processed: 处理总数
            duplicates_found: 发现重复数
            duplicates_removed: 删除重复数
            execution_time: 执行时间
            strategy: 去重策略
        """
        message = f"去重处理完成: 处理{total_processed}条记录, 发现{duplicates_found}条重复, 删除{duplicates_removed}条"

        details = {
            "total_processed": total_processed,
            "duplicates_found": duplicates_found,
            "duplicates_removed": duplicates_removed,
            "strategy": strategy,
        }

        metrics = {
            "total_processed": total_processed,
            "duplicates_found": duplicates_found,
            "duplicates_removed": duplicates_removed,
            "duplicate_rate": (
                duplicates_found / total_processed if total_processed > 0 else 0
            ),
        }

        self.log_operation(
            operation_id=operation_id,
            operation_type=OperationType.DEDUPLICATION,
            status=LogStatus.SUCCESS,
            level=LogLevel.INFO,
            message=message,
            table_name=table_name,
            execution_time=execution_time,
            details=details,
            metrics=metrics,
        )

    def finish_operation(
        self,
        operation_id: str,
        status: LogStatus = LogStatus.SUCCESS,
        final_message: str = "",
        final_metrics: OperationMetrics | None = None,
    ) -> None:
        """结束操作

        Args:
            operation_id: 操作ID
            status: 最终状态
            final_message: 最终消息
            final_metrics: 最终指标
        """
        if operation_id not in self.active_operations:
            self.logger.warning(f"尝试结束不存在的操作: {operation_id}")
            return

        batch_log = self.active_operations[operation_id]
        batch_log.end_time = datetime.now()
        batch_log.status = status

        if final_metrics:
            batch_log.metrics = final_metrics

        # 计算总执行时间
        total_time = (batch_log.end_time - batch_log.start_time).total_seconds()

        message = final_message or f"操作完成: {batch_log.operation_type.value}"

        # 记录结束日志
        self.log_operation(
            operation_id=operation_id,
            operation_type=batch_log.operation_type,
            status=status,
            level=LogLevel.INFO if status == LogStatus.SUCCESS else LogLevel.ERROR,
            message=message,
            execution_time=total_time,
            details=asdict(batch_log.metrics) if batch_log.metrics else None,
        )

        # 从活跃操作中移除
        del self.active_operations[operation_id]

    def get_operation_logs(
        self,
        operation_id: str | None = None,
        operation_type: OperationType | None = None,
        status: LogStatus | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """查询操作日志

        Args:
            operation_id: 操作ID
            operation_type: 操作类型
            status: 状态
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量

        Returns:
            List[Dict[str, Any]]: 日志列表
        """
        query = self.db_session.query(DataQualityLog)

        # 构建查询条件
        conditions = []

        if operation_type:
            conditions.append(DataQualityLog.operation_type == operation_type.value)

        if status:
            conditions.append(DataQualityLog.status == status.value)

        if start_time:
            conditions.append(DataQualityLog.created_at >= start_time)

        if end_time:
            conditions.append(DataQualityLog.created_at <= end_time)

        if conditions:
            query = query.filter(and_(*conditions))

        # 排序和限制
        logs = query.order_by(desc(DataQualityLog.created_at)).limit(limit).all()

        # 转换为字典格式
        result = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "record_id": log.record_id,
                "table_name": log.table_name,
                "operation_type": log.operation_type,
                "status": log.status,
                "message": log.message,
                "error_details": log.error_details,
                "execution_time": log.execution_time,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            result.append(log_dict)

        return result

    def get_operation_statistics(
        self, operation_type: OperationType | None = None, days: int = 7
    ) -> dict[str, Any]:
        """获取操作统计信息

        Args:
            operation_type: 操作类型
            days: 统计天数

        Returns:
            Dict[str, Any]: 统计信息
        """
        start_time = datetime.now() - timedelta(days=days)

        query = self.db_session.query(DataQualityLog).filter(
            DataQualityLog.created_at >= start_time
        )

        if operation_type:
            query = query.filter(DataQualityLog.operation_type == operation_type.value)

        logs = query.all()

        # 统计计算
        total_operations = len(logs)
        success_operations = len([log for log in logs if log.status == "success"])
        failed_operations = len([log for log in logs if log.status == "failed"])

        avg_execution_time = 0.0
        if logs:
            execution_times = [log.execution_time for log in logs if log.execution_time]
            if execution_times:
                avg_execution_time = float(sum(execution_times)) / len(execution_times)

        # 按操作类型分组统计
        operation_type_stats = {}
        for log in logs:
            op_type = log.operation_type
            if op_type not in operation_type_stats:
                operation_type_stats[op_type] = {"total": 0, "success": 0, "failed": 0}

            operation_type_stats[op_type]["total"] += 1
            if log.status == "success":
                operation_type_stats[op_type]["success"] += 1
            elif log.status == "failed":
                operation_type_stats[op_type]["failed"] += 1

        return {
            "period_days": days,
            "total_operations": total_operations,
            "success_operations": success_operations,
            "failed_operations": failed_operations,
            "success_rate": (
                success_operations / total_operations if total_operations > 0 else 0
            ),
            "avg_execution_time": avg_execution_time,
            "operation_type_stats": operation_type_stats,
        }

    def cleanup_old_logs(self) -> int:
        """清理过期日志

        Returns:
            int: 清理的日志数量
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        try:
            # 删除过期日志
            deleted_count = int(
                self.db_session.query(DataQualityLog)
                .filter(DataQualityLog.created_at < cutoff_date)
                .delete()
            )

            # 如果日志数量超过限制，删除最旧的日志
            total_logs = int(self.db_session.query(DataQualityLog).count())
            if total_logs > self.max_log_entries:
                excess_count = total_logs - self.max_log_entries
                oldest_logs = (
                    self.db_session.query(DataQualityLog)
                    .order_by(DataQualityLog.created_at)
                    .limit(excess_count)
                    .all()
                )

                for log in oldest_logs:
                    self.db_session.delete(log)

                deleted_count += excess_count

            self.db_session.commit()

            self.logger.info(f"清理了 {deleted_count} 条过期日志")
            return deleted_count

        except Exception as e:
            self.logger.error(f"清理日志失败: {e!s}")
            self.db_session.rollback()
            return 0

    def _log_to_file(self, log_entry: LogEntry) -> None:
        """记录到文件"""
        log_level = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }.get(log_entry.level, logging.INFO)

        log_message = f"[{log_entry.operation_type.value}] {log_entry.message}"

        extra_info = {
            "operation_id": log_entry.operation_id,
            "status": log_entry.status.value,
            "record_id": log_entry.record_id,
            "table_name": log_entry.table_name,
            "execution_time": log_entry.execution_time,
        }

        self.logger.log(log_level, log_message, extra=extra_info)

    def _log_to_database(self, log_entry: LogEntry) -> None:
        """记录到数据库"""
        try:
            # 对于系统级别的日志（没有具体record_id），使用默认值0
            record_id = log_entry.record_id if log_entry.record_id is not None else 0

            db_log = DataQualityLog(
                record_id=record_id,
                table_name=log_entry.table_name or "system",
                operation_type=log_entry.operation_type.value,
                status=log_entry.status.value,
                message=log_entry.message,
                error_details=log_entry.error_details,
                execution_time=log_entry.execution_time or 0.0,
            )

            self.db_session.add(db_log)
            self.db_session.commit()

        except Exception as e:
            self.logger.error(f"记录日志到数据库失败: {e!s}")
            self.db_session.rollback()

    def _update_batch_operation(self, operation_id: str, log_entry: LogEntry) -> None:
        """更新批量操作状态"""
        if operation_id not in self.active_operations:
            return

        batch_log = self.active_operations[operation_id]

        # 更新指标
        if log_entry.metrics and batch_log.metrics:
            if "total_processed" in log_entry.metrics:
                batch_log.metrics.processed_records += int(
                    log_entry.metrics["total_processed"]
                )
            if "success_records" in log_entry.metrics:
                batch_log.metrics.success_records += int(
                    log_entry.metrics["success_records"]
                )
            if "failed_records" in log_entry.metrics:
                batch_log.metrics.failed_records += int(
                    log_entry.metrics["failed_records"]
                )
            if "duplicates_found" in log_entry.metrics:
                batch_log.metrics.duplicates_found += int(
                    log_entry.metrics["duplicates_found"]
                )
            if "duplicates_removed" in log_entry.metrics:
                batch_log.metrics.duplicates_removed += int(
                    log_entry.metrics["duplicates_removed"]
                )

        # 更新状态
        if log_entry.status == LogStatus.FAILED:
            batch_log.status = LogStatus.FAILED
        elif (
            log_entry.status == LogStatus.IN_PROGRESS
            and batch_log.status == LogStatus.STARTED
        ):
            batch_log.status = LogStatus.IN_PROGRESS
