import asyncio
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from app.data.quality.deduplication_service import DeduplicationReport
from app.data.quality.validation_service import ValidationReport
from app.infrastructure.performance.performance_optimization_service import (
    CacheManager,
    MemoryManager,
    PerformanceConfig,
    PerformanceMetrics,
    PerformanceOptimizationService,
    ProcessingMode,
    performance_monitor,
)


class TestMemoryManager(unittest.TestCase):
    """内存管理器测试类"""

    def setUp(self):
        """测试前置设置"""
        self.memory_manager = MemoryManager(memory_limit_mb=512)

    def test_check_memory_usage(self):
        """测试内存使用量检查"""
        memory_usage = self.memory_manager.check_memory_usage()

        self.assertIsInstance(memory_usage, float)
        self.assertGreater(memory_usage, 0)

    def test_is_memory_available(self):
        """测试内存可用性检查"""
        # 正常情况
        available = self.memory_manager.is_memory_available(10)
        self.assertIsInstance(available, bool)

        # 请求过多内存
        available = self.memory_manager.is_memory_available(1000)
        # 根据实际内存情况，可能返回True或False

    def test_memory_monitor(self):
        """测试内存监控"""
        # 正常阈值
        needs_cleanup = self.memory_manager.memory_monitor(threshold_percent=80.0)
        self.assertIsInstance(needs_cleanup, bool)

        # 低阈值（应该触发清理）
        needs_cleanup = self.memory_manager.memory_monitor(threshold_percent=1.0)
        self.assertTrue(needs_cleanup)

    def test_force_garbage_collection(self):
        """测试强制垃圾回收"""
        # 应该不抛出异常
        try:
            self.memory_manager.force_garbage_collection()
        except Exception as e:
            self.fail(f"垃圾回收失败: {e}")


class TestCacheManager(unittest.TestCase):
    """缓存管理器测试类"""

    def setUp(self):
        """测试前置设置"""
        self.cache_manager = CacheManager(max_size=3)

    def test_cache_operations(self):
        """测试缓存基本操作"""
        # 设置缓存
        self.cache_manager.set_cached_value("key1", "value1")
        self.cache_manager.set_cached_value("key2", "value2")

        # 获取缓存
        value1 = self.cache_manager.get_cached_value("key1")
        self.assertEqual(value1, "value1")

        # 获取不存在的键
        value_none = self.cache_manager.get_cached_value("nonexistent")
        self.assertIsNone(value_none)

    def test_cache_eviction(self):
        """测试缓存淘汰机制"""
        # 填满缓存
        self.cache_manager.set_cached_value("key1", "value1")
        time.sleep(0.01)  # 确保时间差异
        self.cache_manager.set_cached_value("key2", "value2")
        time.sleep(0.01)
        self.cache_manager.set_cached_value("key3", "value3")
        time.sleep(0.01)

        # 添加第四个元素，应该淘汰最旧的
        self.cache_manager.set_cached_value("key4", "value4")

        # key1应该被淘汰
        value1 = self.cache_manager.get_cached_value("key1")
        self.assertIsNone(value1)

        # 其他键应该存在
        value2 = self.cache_manager.get_cached_value("key2")
        self.assertEqual(value2, "value2")

    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        # 初始命中率应该为0
        hit_rate = self.cache_manager.get_hit_rate()
        self.assertEqual(hit_rate, 0.0)

        # 设置缓存
        self.cache_manager.set_cached_value("key1", "value1")

        # 命中
        self.cache_manager.get_cached_value("key1")
        # 未命中
        self.cache_manager.get_cached_value("key2")

        # 命中率应该为0.5
        hit_rate = self.cache_manager.get_hit_rate()
        self.assertEqual(hit_rate, 0.5)

    def test_cache_clear(self):
        """测试缓存清空"""
        # 设置一些缓存
        self.cache_manager.set_cached_value("key1", "value1")
        self.cache_manager.set_cached_value("key2", "value2")

        # 清空缓存
        self.cache_manager.clear()

        # 验证缓存已清空
        value1 = self.cache_manager.get_cached_value("key1")
        self.assertIsNone(value1)

        # 命中率应该重置
        hit_rate = self.cache_manager.get_hit_rate()
        self.assertEqual(hit_rate, 0.0)


class TestPerformanceMonitorDecorator(unittest.TestCase):
    """性能监控装饰器测试类"""

    def test_performance_monitor_success(self):
        """测试性能监控装饰器成功情况"""

        @performance_monitor
        def test_function(x, y):
            time.sleep(0.1)  # 模拟耗时操作
            return x + y

        result = test_function(1, 2)
        self.assertEqual(result, 3)

    def test_performance_monitor_exception(self):
        """测试性能监控装饰器异常情况"""

        @performance_monitor
        def test_function_with_error():
            raise ValueError("测试异常")

        with self.assertRaises(ValueError):
            test_function_with_error()


class TestPerformanceOptimizationService(unittest.TestCase):
    """性能优化服务测试类"""

    def setUp(self):
        """测试前置设置"""
        # 创建模拟的数据库会话
        self.mock_session = Mock(spec=Session)
        self.mock_session.bind = Mock()

        # 创建配置
        self.config = PerformanceConfig(
            batch_size=10,
            max_workers=2,
            chunk_size=5,
            memory_limit_mb=256,
            timeout_seconds=30,
            processing_mode=ProcessingMode.BATCH,
        )

        # 初始化服务
        self.perf_service = PerformanceOptimizationService(
            self.mock_session, self.config
        )

        # 测试数据
        self.test_data = [
            {
                "stock_code": f"{i:06d}",
                "trade_date": "2024-01-15",
                "open_price": 10.0 + i * 0.1,
                "close_price": 10.5 + i * 0.1,
                "high_price": 11.0 + i * 0.1,
                "low_price": 9.5 + i * 0.1,
                "volume": 1000000 + i * 1000,
                "turnover": 10000000.0 + i * 10000,
            }
            for i in range(50)
        ]

    def tearDown(self):
        """测试后清理"""
        self.perf_service.cleanup_resources()

    @patch(
        "app.infrastructure.performance.performance_optimization_service.DataValidationService"
    )
    def test_sequential_validate(self, mock_validation_service_class):
        """测试顺序校验"""
        # 模拟校验服务
        mock_validation_service = Mock()
        mock_validation_service.validate_stock_data.return_value = Mock(
            spec=ValidationReport
        )
        mock_validation_service_class.return_value = mock_validation_service

        # 设置顺序处理模式
        self.perf_service.config.processing_mode = ProcessingMode.SEQUENTIAL

        reports = self.perf_service.batch_validate_data(self.test_data[:5], "A_share")

        self.assertEqual(len(reports), 5)
        self.assertEqual(mock_validation_service.validate_stock_data.call_count, 5)

    @patch(
        "app.infrastructure.performance.performance_optimization_service.DataValidationService"
    )
    def test_batch_validate(self, mock_validation_service_class):
        """测试批量校验"""
        # 模拟校验服务
        mock_validation_service = Mock()
        mock_validation_service.validate_stock_data.return_value = Mock(
            spec=ValidationReport
        )
        mock_validation_service_class.return_value = mock_validation_service

        # 设置批量处理模式
        self.perf_service.config.processing_mode = ProcessingMode.BATCH

        reports = self.perf_service.batch_validate_data(self.test_data[:15], "A_share")

        self.assertEqual(len(reports), 15)
        # 验证批量处理逻辑
        self.assertGreater(mock_validation_service.validate_stock_data.call_count, 0)

    @patch(
        "app.infrastructure.performance.performance_optimization_service.DataValidationService"
    )
    @patch(
        "app.infrastructure.performance.performance_optimization_service.sessionmaker"
    )
    def test_parallel_validate(self, mock_sessionmaker, mock_validation_service_class):
        """测试并行校验"""
        # 模拟会话创建
        mock_session_class = Mock()
        mock_session_instance = Mock()
        mock_session_class.return_value = mock_session_instance
        mock_sessionmaker.return_value = mock_session_class

        # 模拟校验服务
        mock_validation_service = Mock()
        mock_validation_service.validate_stock_data.return_value = Mock(
            spec=ValidationReport
        )
        mock_validation_service_class.return_value = mock_validation_service

        # 设置并行处理模式
        self.perf_service.config.processing_mode = ProcessingMode.PARALLEL

        reports = self.perf_service.batch_validate_data(self.test_data[:10], "A_share")

        self.assertIsInstance(reports, list)
        # 并行处理可能会有不同的结果数量，取决于线程执行情况

    @patch(
        "app.infrastructure.performance.performance_optimization_service.DataDeduplicationService"
    )
    def test_batch_deduplicate_data(self, mock_dedup_service_class):
        """测试批量去重处理"""
        # 模拟去重服务
        mock_dedup_service = Mock()
        mock_dedup_service.find_database_duplicates.return_value = []
        mock_dedup_service_class.return_value = mock_dedup_service

        report = self.perf_service.batch_deduplicate_data("daily_stock_metrics")

        self.assertIsInstance(report, DeduplicationReport)
        mock_dedup_service.find_database_duplicates.assert_called_once()

    def test_async_process_data(self):
        """测试异步数据处理"""

        async def run_async_test():
            # 使用较小的数据集进行异步测试
            small_data = self.test_data[:5]

            with patch(
                "app.infrastructure.performance.performance_optimization_service.DataValidationService"
            ) as mock_service:
                mock_validation_service = Mock()
                mock_validation_service.validate_stock_data.return_value = Mock(
                    spec=ValidationReport
                )
                mock_service.return_value = mock_validation_service

                results = await self.perf_service.async_process_data(
                    small_data, "validation"
                )

                self.assertIsInstance(results, list)
                self.assertLessEqual(len(results), len(small_data))

        # 运行异步测试
        asyncio.run(run_async_test())

    def test_performance_metrics_calculation(self):
        """测试性能指标计算"""
        metrics = PerformanceMetrics(
            start_time=datetime.now(), total_records=100, processed_records=80
        )

        # 设置结束时间
        time.sleep(0.1)
        metrics.end_time = datetime.now()

        # 计算指标
        metrics.calculate_metrics()

        self.assertGreater(metrics.processing_rate, 0)

    def test_get_performance_report(self):
        """测试性能报告生成"""
        # 设置一些指标
        self.perf_service.metrics.total_records = 100
        self.perf_service.metrics.processed_records = 95
        self.perf_service.metrics.error_count = 2

        report = self.perf_service.get_performance_report()

        self.assertIsInstance(report, dict)
        self.assertIn("processing_config", report)
        self.assertIn("performance_metrics", report)
        self.assertIn("recommendations", report)

        # 验证配置信息
        config = report["processing_config"]
        self.assertEqual(config["batch_size"], self.config.batch_size)
        self.assertEqual(config["max_workers"], self.config.max_workers)

        # 验证性能指标
        metrics = report["performance_metrics"]
        self.assertEqual(metrics["total_records"], 100)
        self.assertEqual(metrics["processed_records"], 95)
        self.assertEqual(metrics["error_count"], 2)

        # 验证建议
        recommendations = report["recommendations"]
        self.assertIsInstance(recommendations, list)

    def test_optimization_recommendations(self):
        """测试优化建议生成"""
        # 设置高内存使用
        self.perf_service.metrics.memory_usage_mb = 400  # 接近512MB限制

        # 设置低缓存命中率
        self.perf_service.cache_manager.hit_count = 10
        self.perf_service.cache_manager.miss_count = 90

        # 设置低处理速度
        self.perf_service.metrics.processing_rate = 50

        # 设置高错误率
        self.perf_service.metrics.total_records = 100
        self.perf_service.metrics.error_count = 10

        recommendations = self.perf_service._generate_optimization_recommendations()

        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)

        # 验证建议内容
        recommendation_text = " ".join(recommendations)
        self.assertIn("内存", recommendation_text)
        self.assertIn("缓存", recommendation_text)
        self.assertIn("处理速度", recommendation_text)
        self.assertIn("错误率", recommendation_text)

    def test_memory_management_integration(self):
        """测试内存管理集成"""
        # 测试内存监控
        memory_usage = self.perf_service.memory_manager.check_memory_usage()
        self.assertGreater(memory_usage, 0)

        # 测试内存可用性检查
        available = self.perf_service.memory_manager.is_memory_available(10)
        self.assertIsInstance(available, bool)

    def test_cache_management_integration(self):
        """测试缓存管理集成"""
        # 测试缓存操作
        self.perf_service.cache_manager.set_cached_value("test_key", "test_value")
        value = self.perf_service.cache_manager.get_cached_value("test_key")
        self.assertEqual(value, "test_value")

        # 测试命中率
        hit_rate = self.perf_service.cache_manager.get_hit_rate()
        self.assertGreaterEqual(hit_rate, 0.0)
        self.assertLessEqual(hit_rate, 1.0)

    def test_cleanup_resources(self):
        """测试资源清理"""
        # 应该不抛出异常
        try:
            self.perf_service.cleanup_resources()
        except Exception as e:
            self.fail(f"资源清理失败: {e}")

    def test_concurrent_processing_safety(self):
        """测试并发处理安全性"""
        results = []
        errors = []

        def process_data():
            try:
                with patch(
                    "app.infrastructure.performance.performance_optimization_service.DataValidationService"
                ) as mock_service:
                    mock_validation_service = Mock()
                    mock_validation_service.validate_stock_data.return_value = Mock(
                        spec=ValidationReport
                    )
                    mock_service.return_value = mock_validation_service

                    reports = self.perf_service.batch_validate_data(
                        self.test_data[:5], "A_share"
                    )
                    results.append(reports)
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=process_data)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        self.assertEqual(len(errors), 0)  # 不应该有错误
        self.assertEqual(len(results), 3)  # 应该有3个结果

    def test_performance_with_different_modes(self):
        """测试不同处理模式的性能"""
        modes = [
            ProcessingMode.SEQUENTIAL,
            ProcessingMode.BATCH,
            ProcessingMode.PARALLEL,
        ]

        for mode in modes:
            with self.subTest(mode=mode):
                self.perf_service.config.processing_mode = mode

                with patch(
                    "app.infrastructure.performance.performance_optimization_service.DataValidationService"
                ) as mock_service:
                    mock_validation_service = Mock()
                    mock_validation_service.validate_stock_data.return_value = Mock(
                        spec=ValidationReport
                    )
                    mock_service.return_value = mock_validation_service

                    start_time = time.time()
                    reports = self.perf_service.batch_validate_data(
                        self.test_data[:10], "A_share"
                    )
                    end_time = time.time()

                    processing_time = end_time - start_time

                    # 验证结果
                    self.assertIsInstance(reports, list)
                    self.assertLess(processing_time, 10.0)  # 应该在合理时间内完成

    def test_error_handling_in_processing(self):
        """测试处理过程中的错误处理"""
        with patch(
            "app.infrastructure.performance.performance_optimization_service.DataValidationService"
        ) as mock_service:
            # 模拟校验服务抛出异常
            mock_validation_service = Mock()
            mock_validation_service.validate_stock_data.side_effect = Exception(
                "模拟错误"
            )
            mock_service.return_value = mock_validation_service

            reports = self.perf_service.batch_validate_data(
                self.test_data[:5], "A_share"
            )

            # 应该返回结果（可能为空或部分结果）
            self.assertIsInstance(reports, list)

            # 错误计数应该增加
            self.assertGreater(self.perf_service.metrics.error_count, 0)


if __name__ == "__main__":
    unittest.main()
