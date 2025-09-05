import asyncio
import gc
import logging
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import psutil
from sqlalchemy.orm import Session, sessionmaker

from app.data.quality.deduplication_service import (
    DataDeduplicationService,
    DeduplicationReport,
)
from app.data.quality.validation_service import DataValidationService, ValidationReport


class ProcessingMode(Enum):
    """处理模式枚举"""

    SEQUENTIAL = "sequential"  # 顺序处理
    BATCH = "batch"  # 批量处理
    PARALLEL = "parallel"  # 并行处理
    ASYNC = "async"  # 异步处理
    HYBRID = "hybrid"  # 混合模式


class OptimizationStrategy(Enum):
    """优化策略枚举"""

    MEMORY_OPTIMIZED = "memory_optimized"  # 内存优化
    CPU_OPTIMIZED = "cpu_optimized"  # CPU优化
    IO_OPTIMIZED = "io_optimized"  # IO优化
    BALANCED = "balanced"  # 平衡模式


@dataclass
class PerformanceConfig:
    """性能配置数据类"""

    batch_size: int = 1000
    max_workers: int = 4
    chunk_size: int = 100
    memory_limit_mb: int = 512
    timeout_seconds: int = 300
    enable_caching: bool = True
    cache_size: int = 10000
    processing_mode: ProcessingMode = ProcessingMode.BATCH
    optimization_strategy: OptimizationStrategy = OptimizationStrategy.BALANCED


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    start_time: datetime
    end_time: Optional[datetime] = None
    total_records: int = 0
    processed_records: int = 0
    processing_rate: float = 0.0  # 记录/秒
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hit_rate: float = 0.0
    error_count: int = 0
    warnings_count: int = 0

    def calculate_metrics(self):
        """计算性能指标"""
        if self.end_time and self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
            if duration > 0:
                self.processing_rate = self.processed_records / duration


class MemoryManager:
    """内存管理器"""

    def __init__(self, memory_limit_mb: int = 512):
        self.memory_limit_mb = memory_limit_mb
        self.logger = logging.getLogger(__name__)

    def check_memory_usage(self) -> float:
        """检查当前内存使用量 (MB)"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return float(memory_info.rss) / 1024 / 1024

    def is_memory_available(self, required_mb: float = 0) -> bool:
        """检查是否有足够内存"""
        current_usage = self.check_memory_usage()
        return (current_usage + required_mb) < self.memory_limit_mb

    def force_garbage_collection(self) -> None:
        """强制垃圾回收"""
        gc.collect()
        self.logger.debug("执行垃圾回收")

    def memory_monitor(self, threshold_percent: float = 80.0) -> bool:
        """内存监控，返回是否需要清理"""
        current_usage = self.check_memory_usage()
        usage_percent = (current_usage / self.memory_limit_mb) * 100

        if usage_percent > threshold_percent:
            self.logger.warning(f"内存使用率过高: {usage_percent:.1f}%")
            return True
        return False


class CacheManager:
    """缓存管理器"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, datetime] = {}
        self.hit_count = 0
        self.miss_count = 0
        self.logger = logging.getLogger(__name__)

    def get_cached_value(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            self.access_times[key] = datetime.now()
            self.hit_count += 1
            return self.cache[key]
        else:
            self.miss_count += 1
            return None

    def set_cached_value(self, key: str, value: Any) -> None:
        """设置缓存值"""
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = value
        self.access_times[key] = datetime.now()

    def _evict_oldest(self) -> None:
        """淘汰最旧的缓存项"""
        if not self.access_times:
            return

        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]

    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()
        self.hit_count = 0
        self.miss_count = 0


def performance_monitor(func: Callable) -> Callable:
    """性能监控装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        try:
            result = func(*args, **kwargs)

            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory

            logger = logging.getLogger(func.__module__)
            logger.info(
                f"函数 {func.__name__} 执行完成: "
                f"耗时 {execution_time:.2f}s, "
                f"内存变化 {memory_delta:+.2f}MB"
            )

            return result

        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
            raise

    return wrapper


class PerformanceOptimizationService:
    """性能优化服务类"""

    def __init__(self, db_session: Session, config: Optional[PerformanceConfig] = None):
        self.db_session = db_session
        self.config = config or PerformanceConfig()
        self.logger = logging.getLogger(__name__)

        # 初始化组件
        self.memory_manager = MemoryManager(self.config.memory_limit_mb)
        self.cache_manager = CacheManager(self.config.cache_size)

        # 性能指标
        self.metrics = PerformanceMetrics(start_time=datetime.now())

        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)

        # 进程池 (用于CPU密集型任务)
        self.process_pool = ProcessPoolExecutor(max_workers=min(4, mp.cpu_count()))

    @performance_monitor
    def batch_validate_data(
        self, data_list: List[Dict[str, Any]], market_type: str = "A_share"
    ) -> List[ValidationReport]:
        """批量数据校验

        Args:
            data_list: 数据列表
            market_type: 市场类型

        Returns:
            List[ValidationReport]: 校验报告列表
        """
        self.metrics.total_records = len(data_list)
        self.metrics.start_time = datetime.now()

        if self.config.processing_mode == ProcessingMode.SEQUENTIAL:
            return self._sequential_validate(data_list, market_type)
        elif self.config.processing_mode == ProcessingMode.BATCH:
            return self._batch_validate(data_list, market_type)
        elif self.config.processing_mode == ProcessingMode.PARALLEL:
            return self._parallel_validate(data_list, market_type)
        else:
            return self._batch_validate(data_list, market_type)  # 默认批量处理

    def _sequential_validate(
        self, data_list: List[Dict[str, Any]], market_type: str
    ) -> List[ValidationReport]:
        """顺序校验"""
        validation_service = DataValidationService(self.db_session)
        reports = []

        for i, data in enumerate(data_list):
            try:
                # 内存监控
                if self.memory_manager.memory_monitor():
                    self.memory_manager.force_garbage_collection()

                report = validation_service.validate_stock_data(data, market_type)
                reports.append(report)

                self.metrics.processed_records += 1

                # 进度日志
                if (i + 1) % 100 == 0:
                    self.logger.info(f"已处理 {i + 1}/{len(data_list)} 条记录")

            except Exception as e:
                self.logger.error(f"校验第 {i} 条记录失败: {str(e)}")
                self.metrics.error_count += 1

        self.metrics.end_time = datetime.now()
        self.metrics.calculate_metrics()

        return reports

    def _batch_validate(
        self, data_list: List[Dict[str, Any]], market_type: str
    ) -> List[ValidationReport]:
        """批量校验"""
        validation_service = DataValidationService(self.db_session)
        reports = []

        # 分批处理
        for i in range(0, len(data_list), self.config.batch_size):
            batch = data_list[i : i + self.config.batch_size]

            # 内存检查
            if not self.memory_manager.is_memory_available(50):  # 预留50MB
                self.memory_manager.force_garbage_collection()

            batch_reports = []
            for data in batch:
                try:
                    report = validation_service.validate_stock_data(data, market_type)
                    batch_reports.append(report)
                    self.metrics.processed_records += 1
                except Exception as e:
                    self.logger.error(f"批量校验失败: {str(e)}")
                    self.metrics.error_count += 1

            reports.extend(batch_reports)

            # 批次完成日志
            self.logger.info(
                f"完成批次 {i // self.config.batch_size + 1}, 处理 {len(batch)} 条记录"
            )

        self.metrics.end_time = datetime.now()
        self.metrics.calculate_metrics()

        return reports

    def _parallel_validate(
        self, data_list: List[Dict[str, Any]], market_type: str
    ) -> List[ValidationReport]:
        """并行校验"""
        reports = []

        # 分块处理
        chunks = [
            data_list[i : i + self.config.chunk_size]
            for i in range(0, len(data_list), self.config.chunk_size)
        ]

        # 提交任务到线程池
        future_to_chunk = {
            self.thread_pool.submit(self._validate_chunk, chunk, market_type): chunk
            for chunk in chunks
        }

        # 收集结果
        for future in as_completed(
            future_to_chunk, timeout=self.config.timeout_seconds
        ):
            try:
                chunk_reports = future.result()
                reports.extend(chunk_reports)
                self.metrics.processed_records += len(chunk_reports)
            except Exception as e:
                self.logger.error(f"并行校验块失败: {str(e)}")
                self.metrics.error_count += 1

        self.metrics.end_time = datetime.now()
        self.metrics.calculate_metrics()

        return reports

    def _validate_chunk(
        self, chunk: List[Dict[str, Any]], market_type: str
    ) -> List[ValidationReport]:
        """校验数据块"""
        # 为每个线程创建独立的数据库会话
        engine = self.db_session.bind
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            validation_service = DataValidationService(session)
            reports = []

            for data in chunk:
                try:
                    report = validation_service.validate_stock_data(data, market_type)
                    reports.append(report)
                except Exception as e:
                    self.logger.error(f"校验数据块中的记录失败: {str(e)}")

            return reports

        finally:
            session.close()

    @performance_monitor
    def batch_deduplicate_data(
        self,
        table_name: str = "daily_stock_metrics",
        date_range: Optional[tuple] = None,
    ) -> DeduplicationReport:
        """批量去重处理

        Args:
            table_name: 表名
            date_range: 日期范围

        Returns:
            DeduplicationReport: 去重报告
        """
        dedup_service = DataDeduplicationService(self.db_session)

        # 查找重复组
        duplicate_groups = dedup_service.find_database_duplicates(
            table_name, date_range
        )

        if not duplicate_groups:
            return DeduplicationReport(
                total_processed=0,
                duplicates_found=0,
                duplicates_removed=0,
                duplicate_groups=[],
                execution_time=0.0,
                processed_at=datetime.now(),
            )

        # 批量处理重复组
        if self.config.processing_mode == ProcessingMode.PARALLEL:
            return self._parallel_deduplicate(dedup_service, duplicate_groups)
        else:
            return self._batch_deduplicate(dedup_service, duplicate_groups)

    def _batch_deduplicate(
        self, dedup_service: DataDeduplicationService, duplicate_groups: List
    ) -> DeduplicationReport:
        """批量去重"""
        start_time = datetime.now()
        total_removed = 0

        # 分批处理重复组
        batch_size = min(self.config.batch_size, 100)  # 去重批次不宜过大

        for i in range(0, len(duplicate_groups), batch_size):
            batch_groups = duplicate_groups[i : i + batch_size]

            try:
                removed_count = dedup_service.remove_database_duplicates(batch_groups)
                total_removed += removed_count

                self.logger.info(
                    f"完成去重批次 {i // batch_size + 1}, "
                    f"删除 {removed_count} 条重复记录"
                )

            except Exception as e:
                self.logger.error(f"批量去重失败: {str(e)}")
                self.metrics.error_count += 1

        execution_time = (datetime.now() - start_time).total_seconds()

        return DeduplicationReport(
            total_processed=sum(len(group.records) for group in duplicate_groups),
            duplicates_found=sum(len(group.records) - 1 for group in duplicate_groups),
            duplicates_removed=total_removed,
            duplicate_groups=duplicate_groups,
            execution_time=execution_time,
            processed_at=datetime.now(),
        )

    def _parallel_deduplicate(
        self, dedup_service: DataDeduplicationService, duplicate_groups: List
    ) -> DeduplicationReport:
        """并行去重"""
        start_time = datetime.now()
        total_removed = 0

        # 分块并行处理
        chunks = [
            duplicate_groups[i : i + self.config.chunk_size]
            for i in range(0, len(duplicate_groups), self.config.chunk_size)
        ]

        future_to_chunk = {
            self.thread_pool.submit(self._deduplicate_chunk, chunk): chunk
            for chunk in chunks
        }

        for future in as_completed(
            future_to_chunk, timeout=self.config.timeout_seconds
        ):
            try:
                removed_count = future.result()
                total_removed += removed_count
            except Exception as e:
                self.logger.error(f"并行去重块失败: {str(e)}")
                self.metrics.error_count += 1

        execution_time = (datetime.now() - start_time).total_seconds()

        return DeduplicationReport(
            total_processed=sum(len(group.records) for group in duplicate_groups),
            duplicates_found=sum(len(group.records) - 1 for group in duplicate_groups),
            duplicates_removed=total_removed,
            duplicate_groups=duplicate_groups,
            execution_time=execution_time,
            processed_at=datetime.now(),
        )

    def _deduplicate_chunk(self, chunk: List) -> int:
        """去重数据块"""
        # 为每个线程创建独立的数据库会话
        engine = self.db_session.bind
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            dedup_service = DataDeduplicationService(session)
            return dedup_service.remove_database_duplicates(chunk)
        finally:
            session.close()

    async def async_process_data(
        self, data_list: List[Dict[str, Any]], operation_type: str = "validation"
    ) -> List[Any]:
        """异步数据处理

        Args:
            data_list: 数据列表
            operation_type: 操作类型 (validation, deduplication)

        Returns:
            List[Any]: 处理结果列表
        """
        semaphore = asyncio.Semaphore(self.config.max_workers)

        async def process_item(data: Dict[str, Any]) -> Any:
            async with semaphore:
                loop = asyncio.get_event_loop()

                if operation_type == "validation":
                    validation_service = DataValidationService(self.db_session)
                    return await loop.run_in_executor(
                        self.thread_pool, validation_service.validate_stock_data, data
                    )
                else:
                    # 其他异步操作
                    await asyncio.sleep(0.001)  # 模拟异步操作
                    return data

        # 创建异步任务
        tasks = [process_item(data) for data in data_list]

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果
        valid_results = [r for r in results if not isinstance(r, Exception)]
        error_count = len(results) - len(valid_results)

        if error_count > 0:
            self.logger.warning(f"异步处理中有 {error_count} 个任务失败")

        return valid_results

    def optimize_database_queries(self) -> None:
        """优化数据库查询"""
        try:
            # 分析查询性能
            self.logger.info("开始数据库查询优化")

            # 这里可以添加具体的优化逻辑
            # 例如：创建索引、分析查询计划等

            self.logger.info("数据库查询优化完成")

        except Exception as e:
            self.logger.error(f"数据库查询优化失败: {str(e)}")

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        self.metrics.memory_usage_mb = self.memory_manager.check_memory_usage()
        self.metrics.cache_hit_rate = self.cache_manager.get_hit_rate()

        # CPU使用率
        try:
            self.metrics.cpu_usage_percent = psutil.cpu_percent(interval=1)
        except Exception:
            self.metrics.cpu_usage_percent = 0.0

        return {
            "processing_config": {
                "batch_size": self.config.batch_size,
                "max_workers": self.config.max_workers,
                "processing_mode": self.config.processing_mode.value,
                "optimization_strategy": self.config.optimization_strategy.value,
            },
            "performance_metrics": {
                "total_records": self.metrics.total_records,
                "processed_records": self.metrics.processed_records,
                "processing_rate": self.metrics.processing_rate,
                "memory_usage_mb": self.metrics.memory_usage_mb,
                "cpu_usage_percent": self.metrics.cpu_usage_percent,
                "cache_hit_rate": self.metrics.cache_hit_rate,
                "error_count": self.metrics.error_count,
                "warnings_count": self.metrics.warnings_count,
            },
            "recommendations": self._generate_optimization_recommendations(),
        }

    def _generate_optimization_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 内存使用建议
        if self.metrics.memory_usage_mb > self.config.memory_limit_mb * 0.8:
            recommendations.append("内存使用率过高，建议减少批处理大小或增加内存限制")

        # 缓存命中率建议
        if self.metrics.cache_hit_rate < 0.5:
            recommendations.append("缓存命中率较低，建议增加缓存大小或优化缓存策略")

        # 处理速度建议
        if self.metrics.processing_rate < 100:  # 每秒处理少于100条记录
            recommendations.append("处理速度较慢，建议启用并行处理或优化算法")

        # 错误率建议
        if self.metrics.error_count > self.metrics.total_records * 0.05:  # 错误率超过5%
            recommendations.append("错误率较高，建议检查数据质量和处理逻辑")

        return recommendations

    def cleanup_resources(self) -> None:
        """清理资源"""
        try:
            self.thread_pool.shutdown(wait=True)
            self.process_pool.shutdown(wait=True)
            self.cache_manager.clear()
            self.memory_manager.force_garbage_collection()

            self.logger.info("资源清理完成")

        except Exception as e:
            self.logger.error(f"资源清理失败: {str(e)}")

    def __del__(self):
        """析构函数"""
        self.cleanup_resources()
