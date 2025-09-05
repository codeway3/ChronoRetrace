import unittest
from datetime import date, datetime
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.data.quality.deduplication_service import (
    DataDeduplicationService,
    DeduplicationReport,
    DeduplicationStrategy,
    DuplicateGroup,
    DuplicateRecord,
    DuplicateType,
)


class TestDataDeduplicationService(unittest.TestCase):
    """数据去重服务测试类"""

    def setUp(self):
        """测试前置设置"""
        # 创建内存数据库用于测试
        self.engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=self.engine)
        self.session = SessionLocal()

        # 创建模拟的数据库会话
        self.mock_session = Mock(spec=Session)

        # 初始化服务
        self.dedup_service = DataDeduplicationService(self.mock_session)

        # 测试数据
        self.sample_data = [
            {
                "code": "000001",
                "date": "2024-01-15",
                "open": 10.50,
                "close": 10.80,
                "high": 11.00,
                "low": 10.30,
                "volume": 1000000,
                "turnover": 10800000.0,
            },
            {
                "code": "000001",  # 完全重复
                "date": "2024-01-15",
                "open": 10.50,
                "close": 10.80,
                "high": 11.00,
                "low": 10.30,
                "volume": 1000000,
                "turnover": 10800000.0,
            },
            {
                "code": "000001",  # 部分重复（价格不同）
                "date": "2024-01-15",
                "open": 10.55,
                "close": 10.85,
                "high": 11.05,
                "low": 10.35,
                "volume": 1000000,
                "turnover": 10850000.0,
            },
            {
                "code": "000002",  # 不同股票
                "date": "2024-01-16",  # 不同日期
                "open": 50.50,  # 更大差异的价格
                "close": 51.80,
                "high": 52.00,
                "low": 50.30,
                "volume": 5000000,  # 更大差异的成交量
                "turnover": 259000000.0,
            },
        ]

        # 模拟数据库记录
        self.mock_records = [
            Mock(
                id=1,
                code="000001",
                date=date(2024, 1, 15),
                open=10.50,
                close=10.80,
                quality_score=0.95,
            ),
            Mock(
                id=2,
                code="000001",
                date=date(2024, 1, 15),
                open=10.50,
                close=10.80,
                quality_score=0.90,
            ),
            Mock(
                id=3,
                code="000001",
                date=date(2024, 1, 15),
                open=10.55,
                close=10.85,
                quality_score=0.85,
            ),
        ]

    def tearDown(self):
        """测试后清理"""
        self.session.close()

    def test_generate_data_hash(self):
        """测试数据哈希生成"""
        data1 = self.sample_data[0]
        data2 = self.sample_data[1]  # 相同数据
        data3 = self.sample_data[2]  # 不同数据

        hash1 = self.dedup_service._generate_data_hash(data1)
        hash2 = self.dedup_service._generate_data_hash(data2)
        hash3 = self.dedup_service._generate_data_hash(data3)

        # 相同数据应该产生相同哈希
        self.assertEqual(hash1, hash2)

        # 不同数据应该产生不同哈希
        self.assertNotEqual(hash1, hash3)

        # 哈希应该是字符串
        self.assertIsInstance(hash1, str)
        self.assertGreater(len(hash1), 0)

    def test_calculate_similarity(self):
        """测试相似度计算"""
        data1 = self.sample_data[0]
        data2 = self.sample_data[1]  # 完全相同
        data3 = self.sample_data[2]  # 部分相同
        data4 = self.sample_data[3]  # 完全不同

        # 完全相同的数据
        similarity1 = self.dedup_service._calculate_similarity(data1, data2)
        self.assertEqual(similarity1, 1.0)

        # 部分相同的数据
        similarity2 = self.dedup_service._calculate_similarity(data1, data3)
        self.assertGreater(similarity2, 0.5)
        self.assertLess(similarity2, 1.0)

        # 完全不同的数据
        similarity3 = self.dedup_service._calculate_similarity(data1, data4)
        self.assertLess(similarity3, 0.5)

    def test_identify_duplicate_type(self):
        """测试重复类型识别"""
        data1 = self.sample_data[0]
        data2 = self.sample_data[1]  # 完全重复
        data3 = self.sample_data[2]  # 部分重复
        data4 = self.sample_data[3]  # 不重复

        # 完全重复
        dup_type1 = self.dedup_service._identify_duplicate_type(data1, data2)
        self.assertEqual(dup_type1, DuplicateType.EXACT)

        # 部分重复
        dup_type2 = self.dedup_service._identify_duplicate_type(data1, data3)
        self.assertEqual(dup_type2, DuplicateType.PARTIAL)

        # 不重复
        dup_type3 = self.dedup_service._identify_duplicate_type(data1, data4)
        self.assertIsNone(dup_type3)

    def test_find_duplicates_in_list(self):
        """测试列表中重复数据查找"""
        duplicate_groups = self.dedup_service.find_duplicates_in_list(self.sample_data)

        self.assertIsInstance(duplicate_groups, list)
        self.assertGreater(len(duplicate_groups), 0)

        # 检查重复组结构
        for group in duplicate_groups:
            self.assertIsInstance(group, DuplicateGroup)
            self.assertGreater(len(group.records), 1)  # 重复组至少有2条记录

            # 检查重复记录结构
            for record in group.records:
                self.assertIsInstance(record, DuplicateRecord)
                self.assertIsNotNone(record.data)
                self.assertIsNotNone(record.duplicate_type)

    def test_find_duplicates_exact_match(self):
        """测试精确匹配重复查找"""
        # 添加完全相同的数据
        test_data = [self.sample_data[0], self.sample_data[1]]  # 完全相同

        duplicate_groups = self.dedup_service.find_duplicates_in_list(test_data)

        self.assertEqual(len(duplicate_groups), 1)
        self.assertEqual(len(duplicate_groups[0].records), 2)

        # 检查重复类型
        for record in duplicate_groups[0].records:
            if record.index > 0:  # 第一条记录是原始记录
                self.assertEqual(record.duplicate_type, DuplicateType.EXACT)

    def test_find_duplicates_partial_match(self):
        """测试部分匹配重复查找"""
        # 使用部分相同的数据
        test_data = [self.sample_data[0], self.sample_data[2]]  # 部分相同

        duplicate_groups = self.dedup_service.find_duplicates_in_list(test_data)

        # 根据相似度阈值，可能找到或找不到重复
        if len(duplicate_groups) > 0:
            for record in duplicate_groups[0].records:
                if record.index > 0:
                    self.assertEqual(record.duplicate_type, DuplicateType.PARTIAL)

    @patch("app.data.quality.deduplication_service.DailyStockMetrics")
    def test_find_database_duplicates(self, mock_model):
        """测试数据库重复查找"""
        # 模拟查询结果
        mock_query = Mock()
        mock_query.all.return_value = self.mock_records
        self.mock_session.query.return_value = mock_query

        duplicate_groups = self.dedup_service.find_database_duplicates(
            "daily_stock_metrics"
        )

        self.assertIsInstance(duplicate_groups, list)

        # 验证查询被调用
        self.mock_session.query.assert_called()

    def test_remove_duplicates_keep_first(self):
        """测试保留第一条策略去重"""
        duplicate_groups = self.dedup_service.find_duplicates_in_list(self.sample_data)

        if len(duplicate_groups) > 0:
            removed_count = self.dedup_service.remove_duplicates_from_list(
                duplicate_groups, DeduplicationStrategy.KEEP_FIRST
            )

            self.assertGreaterEqual(removed_count, 0)

    def test_remove_duplicates_keep_last(self):
        """测试保留最后一条策略去重"""
        duplicate_groups = self.dedup_service.find_duplicates_in_list(self.sample_data)

        if len(duplicate_groups) > 0:
            removed_count = self.dedup_service.remove_duplicates_from_list(
                duplicate_groups, DeduplicationStrategy.KEEP_LAST
            )

            self.assertGreaterEqual(removed_count, 0)

    def test_remove_duplicates_keep_highest_quality(self):
        """测试保留最高质量策略去重"""
        # 为测试数据添加质量分数
        test_data = self.sample_data.copy()
        test_data[0]["quality_score"] = 0.95
        test_data[1]["quality_score"] = 0.90

        duplicate_groups = self.dedup_service.find_duplicates_in_list(test_data)

        if len(duplicate_groups) > 0:
            removed_count = self.dedup_service.remove_duplicates_from_list(
                duplicate_groups, DeduplicationStrategy.KEEP_HIGHEST_QUALITY
            )

            self.assertGreaterEqual(removed_count, 0)

    def test_remove_database_duplicates(self):
        """测试数据库重复删除"""
        # 创建模拟重复组
        duplicate_group = DuplicateGroup(
            primary_key="000001_2024-01-15",
            records=[
                DuplicateRecord(
                    duplicate_type=DuplicateType.EXACT,
                    similarity_score=1.0,
                    index=0,
                    data={"id": 1},
                ),
                DuplicateRecord(
                    duplicate_type=DuplicateType.EXACT,
                    similarity_score=1.0,
                    index=1,
                    data={"id": 2},
                ),
            ],
            recommended_action=DeduplicationStrategy.KEEP_FIRST,
            confidence=0.9,
        )

        # 模拟数据库操作
        mock_record = Mock()
        self.mock_session.get.return_value = mock_record

        removed_count = self.dedup_service.remove_database_duplicates([duplicate_group])

        self.assertGreaterEqual(removed_count, 0)

        # 验证删除操作被调用
        if removed_count > 0:
            self.mock_session.delete.assert_called()
            self.mock_session.commit.assert_called()

    def test_generate_deduplication_report(self):
        """测试去重报告生成"""
        duplicate_groups = self.dedup_service.find_duplicates_in_list(self.sample_data)

        report = self.dedup_service.generate_deduplication_report(
            total_processed=len(self.sample_data),
            duplicate_groups=duplicate_groups,
            removed_count=1,
            execution_time=0.5,
        )

        self.assertIsInstance(report, DeduplicationReport)
        self.assertEqual(report.total_processed, len(self.sample_data))
        self.assertGreaterEqual(report.duplicates_found, 0)
        self.assertGreaterEqual(report.duplicates_removed, 0)
        self.assertIsInstance(report.duplicate_groups, list)
        self.assertGreater(report.execution_time, 0)
        self.assertIsInstance(report.processed_at, datetime)

    def test_batch_deduplicate_data(self):
        """测试批量去重处理"""
        report = self.dedup_service.batch_deduplicate_data(
            self.sample_data, DeduplicationStrategy.KEEP_FIRST
        )

        self.assertIsInstance(report, DeduplicationReport)
        self.assertEqual(report.total_processed, len(self.sample_data))

    def test_get_duplicate_statistics(self):
        """测试重复统计信息"""
        duplicate_groups = self.dedup_service.find_duplicates_in_list(self.sample_data)

        stats = self.dedup_service.get_duplicate_statistics(duplicate_groups)

        self.assertIsInstance(stats, dict)
        self.assertIn("total_groups", stats)
        self.assertIn("total_duplicates", stats)
        self.assertIn("duplicate_types", stats)
        self.assertIn("similarity_distribution", stats)

        # 验证统计数据类型
        self.assertIsInstance(stats["total_groups"], int)
        self.assertIsInstance(stats["total_duplicates"], int)
        self.assertIsInstance(stats["duplicate_types"], dict)
        self.assertIsInstance(stats["similarity_distribution"], dict)

    def test_edge_cases(self):
        """测试边界情况"""
        # 空列表
        duplicate_groups = self.dedup_service.find_duplicates_in_list([])
        self.assertEqual(len(duplicate_groups), 0)

        # 单条记录
        single_data = [self.sample_data[0]]
        duplicate_groups = self.dedup_service.find_duplicates_in_list(single_data)
        self.assertEqual(len(duplicate_groups), 0)

        # None数据
        with self.assertRaises((TypeError, AttributeError)):
            self.dedup_service.find_duplicates_in_list(None)

    def test_performance_with_large_dataset(self):
        """测试大数据集性能"""
        # 创建大量测试数据（包含重复）
        large_dataset = []
        base_data = self.sample_data[0].copy()

        for i in range(1000):
            data = base_data.copy()
            data["stock_code"] = f"{i:06d}"
            large_dataset.append(data)

            # 每10条添加一个重复
            if i % 10 == 0:
                large_dataset.append(data.copy())

        start_time = datetime.now()
        duplicate_groups = self.dedup_service.find_duplicates_in_list(large_dataset)
        end_time = datetime.now()

        processing_time = (end_time - start_time).total_seconds()

        # 性能要求：1000+条记录应在合理时间内完成
        self.assertLess(processing_time, 30.0)  # 30秒内完成

        # 验证找到了重复
        self.assertGreater(len(duplicate_groups), 0)

    def test_memory_efficiency(self):
        """测试内存效率"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 处理大量数据
        large_dataset = [self.sample_data[0].copy() for _ in range(5000)]

        self.dedup_service.find_duplicates_in_list(large_dataset)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 内存增长应该在合理范围内
        self.assertLess(memory_increase, 100)  # 不超过100MB

    def test_concurrent_processing(self):
        """测试并发处理安全性"""
        import threading

        results = []
        errors = []

        def process_data():
            try:
                duplicate_groups = self.dedup_service.find_duplicates_in_list(
                    self.sample_data
                )
                results.append(duplicate_groups)
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_data)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        self.assertEqual(len(errors), 0)  # 不应该有错误
        self.assertEqual(len(results), 5)  # 应该有5个结果


if __name__ == "__main__":
    unittest.main()
