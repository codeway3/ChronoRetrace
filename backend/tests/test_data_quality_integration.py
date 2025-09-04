import asyncio
import os
import tempfile
import unittest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.data_deduplication_service import (DataDeduplicationService,
                                                     DeduplicationReport,
                                                     DeduplicationStrategy)
from app.services.data_validation_service import (DataValidationService,
                                                  ValidationReport)
from app.services.error_handling_service import ErrorHandlingService
from app.services.logging_service import (LoggingService, LogLevel, LogStatus,
                                          OperationType)
from app.services.performance_optimization_service import (
    PerformanceConfig, PerformanceOptimizationService, ProcessingMode)


class TestDataQualityIntegration(unittest.TestCase):
    """数据质量模块集成测试类"""

    @classmethod
    def setUpClass(cls):
        """类级别的设置"""
        # 创建临时数据库
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        cls.temp_db.close()

        # 创建数据库引擎
        cls.engine = create_engine(f"sqlite:///{cls.temp_db.name}")

        # 创建表结构
        from app.db.models import Base

        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        """类级别的清理"""
        cls.engine.dispose()
        os.unlink(cls.temp_db.name)

    def setUp(self):
        """测试前置设置"""
        # 创建数据库会话
        SessionLocal = sessionmaker(bind=self.engine)
        self.session = SessionLocal()

        # 初始化服务
        self.validation_service = DataValidationService(self.session)
        self.deduplication_service = DataDeduplicationService(self.session)
        self.error_service = ErrorHandlingService(self.session)
        self.logging_service = LoggingService(self.session)

        # 性能优化配置
        self.perf_config = PerformanceConfig(
            batch_size=50,
            max_workers=2,
            chunk_size=10,
            processing_mode=ProcessingMode.BATCH,
        )
        self.perf_service = PerformanceOptimizationService(
            self.session, self.perf_config
        )

        # 测试数据集
        self.test_dataset = self._create_test_dataset()

    def tearDown(self):
        """测试后清理"""
        self.session.close()
        self.perf_service.cleanup_resources()

    def _create_test_dataset(self) -> List[Dict[str, Any]]:
        """创建测试数据集"""
        dataset = []

        # 有效数据
        for i in range(20):
            dataset.append(
                {
                    "code": f"{i + 1:06d}",
                    "date": "2024-01-15",
                    "open": 10.0 + i * 0.1,
                    "close": 10.5 + i * 0.1,
                    "high": 11.0 + i * 0.1,
                    "low": 9.5 + i * 0.1,
                    "volume": 1000000 + i * 1000,
                    "turnover": 10000000.0 + i * 10000,
                    "pe_ratio": 15.0 + i * 0.1,
                    "market_cap": 100000000.0 + i * 1000000,
                }
            )

        # 重复数据
        dataset.append(dataset[0].copy())  # 完全重复
        dataset.append(dataset[1].copy())  # 完全重复

        # 部分重复数据
        partial_duplicate = dataset[2].copy()
        partial_duplicate["open_price"] = 12.1  # 稍微不同
        dataset.append(partial_duplicate)

        # 无效数据
        invalid_data = [
            {
                "code": "",  # 空股票代码
                "date": "2024-01-15",
                "open": 10.0,
                "close": 10.5,
                "high": 11.0,
                "low": 9.5,
                "volume": 1000000,
                "turnover": 10000000.0,
            },
            {
                "code": "000001",
                "date": "2024-13-45",  # 无效日期
                "open": 10.0,
                "close": 10.5,
                "high": 11.0,
                "low": 9.5,
                "volume": 1000000,
                "turnover": 10000000.0,
            },
            {
                "code": "000002",
                "date": "2024-01-15",
                "open": -10.0,  # 负价格
                "close": 10.5,
                "high": 11.0,
                "low": 9.5,
                "volume": 1000000,
                "turnover": 10000000.0,
            },
            {
                "code": "000003",
                "date": "2024-01-15",
                "open": 10.0,
                "close": 10.5,
                "high": 8.0,  # 最高价小于开盘价
                "low": 9.5,
                "volume": 1000000,
                "turnover": 10000000.0,
            },
            {
                "code": "000004",
                "date": "2024-01-15",
                "open": 10.0,
                "close": 10.5,
                "high": 11.0,
                "low": 9.5,
                "volume": -1000000,  # 负成交量
                "turnover": 10000000.0,
            },
        ]

        dataset.extend(invalid_data)
        return dataset

    def test_complete_data_quality_workflow(self):
        """测试完整的数据质量工作流程"""
        # 1. 数据校验阶段
        validation_reports = self.validation_service.batch_validate_data(
            self.test_dataset, "A_share"
        )

        self.assertEqual(len(validation_reports), len(self.test_dataset))

        # 统计校验结果
        valid_count = sum(1 for report in validation_reports if report.is_valid)
        invalid_count = len(validation_reports) - valid_count

        self.assertGreater(valid_count, 0)  # 应该有有效数据
        self.assertGreater(invalid_count, 0)  # 应该有无效数据

        # 2. 去重阶段
        duplicate_groups = self.deduplication_service.find_duplicates_in_list(
            self.test_dataset
        )

        self.assertGreater(len(duplicate_groups), 0)  # 应该找到重复数据

        # 执行去重
        dedup_report = self.deduplication_service.batch_deduplicate_data(
            self.test_dataset, DeduplicationStrategy.KEEP_FIRST
        )

        self.assertIsInstance(dedup_report, DeduplicationReport)
        deduplicated_data = dedup_report.deduplicated_data
        self.assertIsInstance(deduplicated_data, list)
        self.assertLess(
            len(deduplicated_data), len(self.test_dataset)
        )  # 去重后数据应该减少

        # 3. 日志记录
        self.logging_service.log_operation(
            operation_id=f"workflow_{int(datetime.now().timestamp())}",
            operation_type=OperationType.VALIDATION,
            status=LogStatus.SUCCESS,
            level=LogLevel.INFO,
            message=f"处理了 {len(self.test_dataset)} 条记录",
            record_id=1,  # 提供一个有效的record_id
            table_name="test_data",
            details={
                "valid_count": valid_count,
                "invalid_count": invalid_count,
            },
        )

        # 验证日志记录成功（通过没有抛出异常来验证）
        self.assertTrue(True)

    def test_performance_optimization_integration(self):
        """测试性能优化集成"""
        # 使用性能优化服务进行批量校验
        start_time = datetime.now()

        with patch(
            "app.services.performance_optimization_service.DataValidationService"
        ) as mock_service:
            mock_validation_service = Mock()
            mock_validation_service.validate_stock_data.return_value = Mock(
                spec=ValidationReport
            )
            mock_service.return_value = mock_validation_service

            reports = self.perf_service.batch_validate_data(
                self.test_dataset, "A_share"
            )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # 验证结果
        self.assertEqual(len(reports), len(self.test_dataset))
        self.assertLess(processing_time, 10.0)  # 应该在合理时间内完成

        # 获取性能报告
        perf_report = self.perf_service.get_performance_report()

        self.assertIsInstance(perf_report, dict)
        self.assertIn("performance_metrics", perf_report)
        self.assertIn("recommendations", perf_report)

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 模拟处理过程中的错误
        try:
            # 故意传入无效数据类型
            invalid_input = "这不是一个字典"
            self.validation_service.validate_stock_data(invalid_input, "A_share")
        except Exception as e:
            # 使用错误处理服务处理异常
            error_response = self.error_service.handle_exception(
                exception=e,
                context={
                    "operation": "data_validation",
                    "input_type": type(invalid_input).__name__,
                },
            )

            self.assertIsNotNone(error_response)
            self.assertIn("error_message", error_response)
            self.assertIn("suggested_action", error_response)

    def test_concurrent_processing_integration(self):
        """测试并发处理集成"""
        import threading

        results = []
        errors = []

        def process_batch(batch_data):
            try:
                # 校验
                validation_reports = self.validation_service.batch_validate_data(
                    batch_data, "A_share"
                )

                # 去重
                duplicate_groups = self.deduplication_service.find_duplicates_in_list(
                    batch_data
                )

                results.append(
                    {
                        "validation_reports": validation_reports,
                        "duplicate_groups": duplicate_groups,
                    }
                )

            except Exception as e:
                errors.append(e)

        # 将数据分成多个批次
        batch_size = 10
        batches = [
            self.test_dataset[i : i + batch_size]
            for i in range(0, len(self.test_dataset), batch_size)
        ]

        # 创建多个线程处理不同批次
        threads = []
        for batch in batches:
            thread = threading.Thread(target=process_batch, args=(batch,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        self.assertEqual(len(errors), 0)  # 不应该有错误
        self.assertEqual(len(results), len(batches))  # 应该有对应数量的结果

    def test_async_processing_integration(self):
        """测试异步处理集成"""

        async def async_workflow():
            # 异步校验
            validation_results = await self.perf_service.async_process_data(
                self.test_dataset[:10], "validation"
            )

            self.assertIsInstance(validation_results, list)
            self.assertLessEqual(len(validation_results), 10)

            return validation_results

        # 运行异步工作流
        results = asyncio.run(async_workflow())
        self.assertIsInstance(results, list)

    def test_data_quality_metrics_collection(self):
        """测试数据质量指标收集"""
        # 执行完整的数据质量检查
        validation_reports = self.validation_service.batch_validate_data(
            self.test_dataset, "A_share"
        )

        duplicate_groups = self.deduplication_service.find_duplicates_in_list(
            self.test_dataset
        )

        # 收集质量指标
        quality_metrics = {
            "total_records": len(self.test_dataset),
            "valid_records": sum(1 for r in validation_reports if r.is_valid),
            "invalid_records": sum(1 for r in validation_reports if not r.is_valid),
            "duplicate_groups": len(duplicate_groups),
            "total_duplicates": sum(
                len(group.records) - 1 for group in duplicate_groups
            ),
            "average_quality_score": sum(r.quality_score for r in validation_reports)
            / len(validation_reports),
            "validation_errors": sum(len(r.errors) for r in validation_reports),
            "validation_warnings": sum(len(r.warnings) for r in validation_reports),
        }

        # 验证指标
        self.assertEqual(quality_metrics["total_records"], len(self.test_dataset))
        self.assertGreater(quality_metrics["valid_records"], 0)
        self.assertGreater(quality_metrics["invalid_records"], 0)
        self.assertGreaterEqual(quality_metrics["duplicate_groups"], 0)
        self.assertGreaterEqual(quality_metrics["average_quality_score"], 0.0)
        self.assertLessEqual(quality_metrics["average_quality_score"], 1.0)

        # 记录质量指标
        self.logging_service.log_operation(
            operation_id=f"quality_check_{int(datetime.now().timestamp())}",
            operation_type=OperationType.QUALITY_CHECK,
            status=LogStatus.SUCCESS,
            level=LogLevel.INFO,
            message="数据质量检查完成",
            details=quality_metrics,
        )

    def test_memory_management_during_processing(self):
        """测试处理过程中的内存管理"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 处理大量数据
        large_dataset = self.test_dataset * 10  # 扩大数据集

        # 使用内存管理的批量处理
        validation_reports = self.validation_service.batch_validate_data(
            large_dataset, "A_share"
        )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 验证内存使用在合理范围内
        self.assertLess(memory_increase, 200)  # 内存增长不超过200MB

        # 验证处理结果
        self.assertEqual(len(validation_reports), len(large_dataset))

    def test_error_recovery_and_resilience(self):
        """测试错误恢复和系统韧性"""
        # 创建包含各种错误的数据集
        problematic_dataset = [
            None,  # None值
            {},  # 空字典
            {"invalid": "data"},  # 缺少必要字段
            {"stock_code": "000001", "trade_date": "invalid_date"},  # 无效日期
        ]

        # 系统应该能够处理这些错误而不崩溃
        try:
            validation_reports = self.validation_service.batch_validate_data(
                problematic_dataset, "A_share"
            )

            # 应该返回报告，即使有错误
            self.assertIsInstance(validation_reports, list)

            # 所有报告都应该标记为无效
            for report in validation_reports:
                if report is not None:
                    self.assertFalse(report.is_valid)

        except Exception as e:
            # 如果抛出异常，应该被错误处理服务捕获
            error_response = self.error_service.handle_exception(
                exception=e,
                context={"operation": "batch_validation", "data_type": "problematic"},
            )

            self.assertIsNotNone(error_response)

    def test_end_to_end_data_pipeline(self):
        """测试端到端数据管道"""
        pipeline_start = datetime.now()

        # 阶段1: 数据校验
        validation_start = datetime.now()
        validation_reports = self.validation_service.batch_validate_data(
            self.test_dataset, "A_share"
        )
        validation_time = (datetime.now() - validation_start).total_seconds()

        # 阶段2: 数据去重
        dedup_start = datetime.now()
        duplicate_groups = self.deduplication_service.find_duplicates_in_list(
            self.test_dataset
        )
        dedup_report = self.deduplication_service.batch_deduplicate_data(
            self.test_dataset, DeduplicationStrategy.KEEP_HIGHEST_QUALITY
        )
        deduplicated_data = dedup_report.deduplicated_data
        duplicates_removed = len(self.test_dataset) - len(deduplicated_data)
        dedup_time = (datetime.now() - dedup_start).total_seconds()

        # 阶段3: 结果汇总
        summary_start = datetime.now()

        pipeline_summary = {
            "pipeline_start": pipeline_start,
            "pipeline_end": datetime.now(),
            "total_time": (datetime.now() - pipeline_start).total_seconds(),
            "validation_time": validation_time,
            "deduplication_time": dedup_time,
            "total_records": len(self.test_dataset),
            "valid_records": sum(1 for r in validation_reports if r.is_valid),
            "invalid_records": sum(1 for r in validation_reports if not r.is_valid),
            "duplicate_groups_found": len(duplicate_groups),
            "duplicates_removed": duplicates_removed,
            "average_quality_score": sum(r.quality_score for r in validation_reports)
            / len(validation_reports),
            "processing_rate": len(self.test_dataset)
            / (datetime.now() - pipeline_start).total_seconds(),
        }

        summary_time = (datetime.now() - summary_start).total_seconds()
        pipeline_summary["summary_time"] = summary_time

        # 验证管道执行结果
        self.assertGreater(pipeline_summary["total_records"], 0)
        self.assertGreaterEqual(pipeline_summary["valid_records"], 0)
        self.assertGreaterEqual(pipeline_summary["invalid_records"], 0)
        self.assertGreaterEqual(pipeline_summary["duplicate_groups_found"], 0)
        self.assertGreater(pipeline_summary["processing_rate"], 0)

        # 性能要求
        self.assertLess(pipeline_summary["total_time"], 30.0)  # 总时间不超过30秒
        self.assertGreater(
            pipeline_summary["processing_rate"], 1.0
        )  # 每秒至少处理1条记录

        # 记录管道执行日志
        self.logging_service.log_operation(
            operation_id=f"pipeline_{int(pipeline_start.timestamp())}",
            operation_type=OperationType.PIPELINE,
            status=LogStatus.SUCCESS,
            level=LogLevel.INFO,
            message="数据质量管道执行完成",
            details=pipeline_summary,
        )

        return pipeline_summary


if __name__ == "__main__":
    unittest.main()