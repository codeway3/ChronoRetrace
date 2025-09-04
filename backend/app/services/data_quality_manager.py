import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .data_deduplication_service import (DataDeduplicationService,
                                         DeduplicationReport,
                                         DeduplicationStrategy)
from .data_validation_service import DataValidationService, ValidationReport
from .error_handling_service import ErrorHandlingService
from .logging_service import LoggingService, LogStatus, OperationType
from .performance_optimization_service import (PerformanceConfig,
                                               PerformanceOptimizationService,
                                               ProcessingMode)


@dataclass
class DataQualityConfig:
    """数据质量配置"""

    enable_validation: bool = True
    enable_deduplication: bool = True
    enable_performance_optimization: bool = True
    enable_logging: bool = True

    # 校验配置
    validation_rules: Optional[Dict[str, Any]] = None

    # 去重配置
    deduplication_strategy: DeduplicationStrategy = DeduplicationStrategy.KEEP_FIRST
    similarity_threshold: float = 0.95

    # 性能配置
    batch_size: int = 100
    max_workers: int = 4
    processing_mode: ProcessingMode = ProcessingMode.BATCH

    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    log_to_database: bool = True


@dataclass
class DataQualityResult:
    """数据质量处理结果"""

    success: bool
    total_records: int
    valid_records: int
    invalid_records: int
    duplicates_found: int
    duplicates_removed: int
    processing_time: float
    quality_score: float
    validation_reports: List[ValidationReport]
    deduplication_report: Optional[DeduplicationReport]
    error_messages: List[str]
    warnings: List[str]
    performance_metrics: Dict[str, Any]


class DataQualityManager:
    """数据质量管理器 - 统一的数据质量处理入口"""

    def __init__(self, session: Session, config: Optional[DataQualityConfig] = None):
        """
        初始化数据质量管理器

        Args:
            session: 数据库会话
            config: 数据质量配置
        """
        self.session = session
        self.config = config or DataQualityConfig()

        # 初始化服务组件
        self._init_services()

        # 设置日志
        self._setup_logging()

    def _init_services(self):
        """初始化服务组件"""
        # 核心服务
        if self.config.enable_validation:
            self.validation_service = DataValidationService(self.session)

        if self.config.enable_deduplication:
            self.deduplication_service = DataDeduplicationService(self.session)

        # 支持服务
        self.error_service = ErrorHandlingService()

        if self.config.enable_logging:
            self.logging_service = LoggingService()

        # 性能优化服务
        if self.config.enable_performance_optimization:
            perf_config = PerformanceConfig(
                batch_size=self.config.batch_size,
                max_workers=self.config.max_workers,
                processing_mode=self.config.processing_mode,
            )
            self.performance_service = PerformanceOptimizationService(
                self.session, perf_config
            )

    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def process_data(
        self, data: List[Dict[str, Any]], data_type: str = "A_share"
    ) -> DataQualityResult:
        """
        处理数据质量 - 主要入口方法

        Args:
            data: 待处理的数据列表
            data_type: 数据类型

        Returns:
            DataQualityResult: 处理结果
        """
        start_time = datetime.now()

        try:
            self.logger.info(f"开始处理数据质量，数据量: {len(data)}")

            # 记录开始日志
            if self.config.enable_logging:
                self.logging_service.log_operation(
                    operation_type=OperationType.PIPELINE,
                    status=LogStatus.IN_PROGRESS,
                    message=f"开始处理 {len(data)} 条 {data_type} 数据",
                )

            # 初始化结果
            result = DataQualityResult(
                success=False,
                total_records=len(data),
                valid_records=0,
                invalid_records=0,
                duplicates_found=0,
                duplicates_removed=0,
                processing_time=0.0,
                quality_score=0.0,
                validation_reports=[],
                deduplication_report=None,
                error_messages=[],
                warnings=[],
                performance_metrics={},
            )

            # 阶段1: 数据校验
            if self.config.enable_validation:
                validation_result = self._validate_data(data, data_type)
                result.validation_reports = validation_result["reports"]
                result.valid_records = validation_result["valid_count"]
                result.invalid_records = validation_result["invalid_count"]
                result.quality_score = validation_result["quality_score"]
                result.warnings.extend(validation_result["warnings"])

            # 阶段2: 数据去重
            if self.config.enable_deduplication:
                dedup_result = self._deduplicate_data(data)
                result.deduplication_report = dedup_result["report"]
                result.duplicates_found = dedup_result["duplicates_found"]
                result.duplicates_removed = dedup_result["duplicates_removed"]
                result.warnings.extend(dedup_result["warnings"])

            # 阶段3: 性能指标收集
            if self.config.enable_performance_optimization:
                perf_metrics = self._collect_performance_metrics(start_time)
                result.performance_metrics = perf_metrics

            # 计算处理时间
            end_time = datetime.now()
            result.processing_time = (end_time - start_time).total_seconds()

            # 标记成功
            result.success = True

            # 记录成功日志
            if self.config.enable_logging:
                self.logging_service.log_operation(
                    operation_type=OperationType.PIPELINE,
                    status=LogStatus.SUCCESS,
                    message="数据质量处理完成",
                    details={
                        "total_records": result.total_records,
                        "valid_records": result.valid_records,
                        "invalid_records": result.invalid_records,
                        "duplicates_found": result.duplicates_found,
                        "duplicates_removed": result.duplicates_removed,
                        "processing_time": result.processing_time,
                        "quality_score": result.quality_score,
                    },
                )

            self.logger.info(f"数据质量处理完成，耗时: {result.processing_time:.2f}秒")

            return result

        except Exception as e:
            # 错误处理
            error_response = self.error_service.handle_exception(
                exception=e,
                context={
                    "operation": "data_quality_processing",
                    "data_count": len(data),
                    "data_type": data_type,
                },
            )

            # 记录错误日志
            if self.config.enable_logging:
                self.logging_service.log_operation(
                    operation_type=OperationType.PIPELINE,
                    status=LogStatus.ERROR,
                    message=f"数据质量处理失败: {str(e)}",
                    error_details=error_response,
                )

            self.logger.error(f"数据质量处理失败: {str(e)}")

            # 返回错误结果
            end_time = datetime.now()
            result = DataQualityResult(
                success=False,
                total_records=len(data),
                valid_records=0,
                invalid_records=0,
                duplicates_found=0,
                duplicates_removed=0,
                processing_time=(end_time - start_time).total_seconds(),
                quality_score=0.0,
                validation_reports=[],
                deduplication_report=None,
                error_messages=[error_response.get("error_message", str(e))],
                warnings=[],
                performance_metrics={},
            )

            return result

    def _validate_data(
        self, data: List[Dict[str, Any]], data_type: str
    ) -> Dict[str, Any]:
        """执行数据校验"""
        try:
            if self.config.enable_performance_optimization:
                # 使用性能优化的批量校验
                reports = self.performance_service.batch_validate_data(data, data_type)
            else:
                # 使用标准批量校验
                reports = self.validation_service.batch_validate_data(data, data_type)

            valid_count = sum(1 for r in reports if r.is_valid)
            invalid_count = len(reports) - valid_count
            quality_score = (
                sum(r.quality_score for r in reports) / len(reports) if reports else 0.0
            )

            warnings = []
            if invalid_count > 0:
                warnings.append(f"发现 {invalid_count} 条无效数据")

            return {
                "reports": reports,
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "quality_score": quality_score,
                "warnings": warnings,
            }

        except Exception as e:
            self.logger.error(f"数据校验失败: {str(e)}")
            raise

    def _deduplicate_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行数据去重"""
        try:
            # 查找重复数据
            duplicate_groups = self.deduplication_service.find_duplicates_in_list(data)
            duplicates_found = len(duplicate_groups)

            # 执行去重
            if duplicates_found > 0:
                if self.config.enable_performance_optimization:
                    # 使用性能优化的批量去重
                    dedup_report = self.performance_service.batch_deduplicate_data(
                        data, self.config.deduplication_strategy
                    )
                else:
                    # 使用标准批量去重
                    dedup_report = self.deduplication_service.batch_deduplicate_data(
                        data, self.config.deduplication_strategy
                    )

                duplicates_removed = dedup_report.duplicates_removed
            else:
                dedup_report = None
                duplicates_removed = 0

            warnings = []
            if duplicates_found > 0:
                warnings.append(
                    f"发现 {duplicates_found} 组重复数据，移除 {duplicates_removed} 条"
                )

            return {
                "report": dedup_report,
                "duplicates_found": duplicates_found,
                "duplicates_removed": duplicates_removed,
                "warnings": warnings,
            }

        except Exception as e:
            self.logger.error(f"数据去重失败: {str(e)}")
            raise

    def _collect_performance_metrics(self, start_time: datetime) -> Dict[str, Any]:
        """收集性能指标"""
        try:
            if hasattr(self, "performance_service"):
                return self.performance_service.get_performance_report()
            else:
                current_time = datetime.now()
                return {
                    "processing_start": start_time,
                    "processing_current": current_time,
                    "elapsed_time": (current_time - start_time).total_seconds(),
                }
        except Exception as e:
            self.logger.warning(f"性能指标收集失败: {str(e)}")
            return {}

    def validate_only(
        self, data: List[Dict[str, Any]], data_type: str = "A_share"
    ) -> List[ValidationReport]:
        """
        仅执行数据校验

        Args:
            data: 待校验的数据
            data_type: 数据类型

        Returns:
            List[ValidationReport]: 校验报告列表
        """
        if not self.config.enable_validation:
            raise ValueError("数据校验功能未启用")

        return self.validation_service.batch_validate_data(data, data_type)

    def deduplicate_only(
        self,
        data: List[Dict[str, Any]],
        strategy: Optional[DeduplicationStrategy] = None,
    ) -> DeduplicationReport:
        """
        仅执行数据去重

        Args:
            data: 待去重的数据
            strategy: 去重策略

        Returns:
            DeduplicationReport: 去重报告
        """
        if not self.config.enable_deduplication:
            raise ValueError("数据去重功能未启用")

        strategy = strategy or self.config.deduplication_strategy
        return self.deduplication_service.batch_deduplicate_data(data, strategy)

    def get_quality_statistics(self) -> Dict[str, Any]:
        """
        获取数据质量统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            if self.config.enable_logging:
                return self.logging_service.get_operation_statistics()
            else:
                return {"message": "日志功能未启用，无法获取统计信息"}
        except Exception as e:
            self.logger.error(f"获取质量统计失败: {str(e)}")
            return {"error": str(e)}

    def cleanup_resources(self):
        """清理资源"""
        try:
            if hasattr(self, "performance_service"):
                self.performance_service.cleanup_resources()

            if hasattr(self, "logging_service"):
                self.logging_service.cleanup_old_logs()

            self.logger.info("资源清理完成")

        except Exception as e:
            self.logger.error(f"资源清理失败: {str(e)}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup_resources()


# 便捷函数
def create_data_quality_manager(
    session: Session, config: Optional[DataQualityConfig] = None
) -> DataQualityManager:
    """
    创建数据质量管理器的便捷函数

    Args:
        session: 数据库会话
        config: 配置对象

    Returns:
        DataQualityManager: 数据质量管理器实例
    """
    return DataQualityManager(session, config)


def quick_quality_check(
    session: Session, data: List[Dict[str, Any]], data_type: str = "A_share"
) -> DataQualityResult:
    """
    快速数据质量检查的便捷函数

    Args:
        session: 数据库会话
        data: 待检查的数据
        data_type: 数据类型

    Returns:
        DataQualityResult: 检查结果
    """
    with create_data_quality_manager(session) as manager:
        return manager.process_data(data, data_type)
