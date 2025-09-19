from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Union

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (  # type: ignore
    DailyStockMetrics,
    DataQualityLog,
)


class DeduplicationStrategy(Enum):
    """去重策略枚举"""

    KEEP_FIRST = "keep_first"  # 保留第一条
    KEEP_LAST = "keep_last"  # 保留最后一条
    KEEP_HIGHEST_QUALITY = "keep_highest_quality"  # 保留质量最高的
    MERGE_RECORDS = "merge_records"  # 合并数据


class DuplicateType(Enum):
    """重复类型枚举"""

    EXACT = "exact"  # 完全重复
    PARTIAL = "partial"  # 部分重复
    SIMILAR = "similar"  # 相似重复


@dataclass
class DuplicateRecord:
    """重复记录数据类"""

    duplicate_type: DuplicateType
    similarity_score: float  # 0.0 - 1.0
    record_id: Union[int, None] = None
    conflicting_fields: Union[list[str], None] = None
    data_source: Union[str, None] = None
    quality_score: float = 0.0
    created_at: Union[datetime, None] = None
    index: Union[int, None] = None  # 记录在列表中的索引
    data: Union[dict[str, Any], None] = None  # 记录的实际数据


@dataclass
class DuplicateGroup:
    """重复组数据类"""

    primary_key: str  # 主键标识 (如: code_date)
    records: list[DuplicateRecord]
    recommended_action: DeduplicationStrategy
    confidence: float  # 推荐置信度


@dataclass
class DeduplicationReport:
    """去重报告数据类"""

    total_processed: int
    duplicates_found: int
    duplicates_removed: int
    duplicate_groups: list[DuplicateGroup]
    execution_time: float
    processed_at: datetime
    deduplicated_data: Union[list[dict[str, Any]], None] = (
        None  # 去重后的数据，用于向后兼容
    )


class DataDeduplicationService:
    """数据去重服务类"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

        # 字段权重配置 (用于相似度计算)
        self.field_weights = {
            "code": 0.3,
            "date": 0.3,
            "close": 0.2,
            "volume": 0.1,
            "open": 0.05,
            "high": 0.025,
            "low": 0.025,
        }

        # 相似度阈值
        self.similarity_thresholds = {"exact": 1.0, "partial": 0.8, "similar": 0.6}

    def deduplicate_stock_data(
        self,
        data_list: list[dict[str, Any]],
        strategy: DeduplicationStrategy = DeduplicationStrategy.KEEP_HIGHEST_QUALITY,
    ) -> DeduplicationReport:
        """对股票数据进行去重处理

        Args:
            data_list: 股票数据列表
            strategy: 去重策略

        Returns:
            DeduplicationReport: 去重报告
        """
        start_time = datetime.now()

        # 构建唯一键索引
        unique_key_groups = self._group_by_unique_key(data_list)

        # 识别重复组
        duplicate_groups = []
        for key, records in unique_key_groups.items():
            if len(records) > 1:
                duplicate_group = self._analyze_duplicate_group(key, records)
                duplicate_groups.append(duplicate_group)

        # 执行去重操作
        duplicates_removed = 0
        for group in duplicate_groups:
            removed_count = self._apply_deduplication_strategy(group, strategy)
            duplicates_removed += removed_count

        execution_time = (datetime.now() - start_time).total_seconds()

        return DeduplicationReport(
            total_processed=len(data_list),
            duplicates_found=sum(len(group.records) - 1 for group in duplicate_groups),
            duplicates_removed=duplicates_removed,
            duplicate_groups=duplicate_groups,
            execution_time=execution_time,
            processed_at=datetime.now(),
        )

    def _generate_data_hash(self, data: dict[str, Any]) -> str:
        """生成数据哈希值"""
        # 创建一个排序后的字符串表示
        sorted_items = sorted(data.items())
        data_str = str(sorted_items)
        return hashlib.md5(data_str.encode(), usedforsecurity=False).hexdigest()

    def _identify_duplicate_type(
        self, data1: dict[str, Any], data2: dict[str, Any]
    ) -> Union[DuplicateType, None]:
        """识别重复类型"""
        similarity = self._calculate_similarity(data1, data2)

        if similarity >= self.similarity_thresholds["exact"]:
            return DuplicateType.EXACT
        elif similarity >= self.similarity_thresholds["partial"]:
            return DuplicateType.PARTIAL
        elif similarity >= self.similarity_thresholds["similar"]:
            return DuplicateType.SIMILAR
        else:
            return None

    def remove_duplicates_from_list(
        self, duplicate_groups: list[DuplicateGroup], strategy: DeduplicationStrategy
    ) -> int:
        """从列表中移除重复数据"""
        removed_count = 0

        for group in duplicate_groups:
            if len(group.records) <= 1:
                continue

            # 根据策略选择要保留的记录
            if strategy == DeduplicationStrategy.KEEP_FIRST:
                to_remove = group.records[1:]  # 保留第一个，移除其余
            elif strategy == DeduplicationStrategy.KEEP_LAST:
                to_remove = group.records[:-1]  # 保留最后一个，移除其余
            elif strategy == DeduplicationStrategy.KEEP_HIGHEST_QUALITY:
                # 按质量分数排序，保留最高的
                sorted_records = sorted(
                    group.records, key=lambda x: x.quality_score, reverse=True
                )
                to_remove = sorted_records[1:]  # 保留质量最高的，移除其余
            else:
                to_remove = group.records[1:]  # 默认保留第一个

            removed_count += len(to_remove)

        return removed_count

    def generate_deduplication_report(
        self,
        total_processed: int,
        duplicate_groups: list[DuplicateGroup],
        removed_count: int,
        execution_time: float,
    ) -> DeduplicationReport:
        """生成去重报告"""
        duplicates_found = sum(len(group.records) for group in duplicate_groups)

        return DeduplicationReport(
            total_processed=total_processed,
            duplicates_found=duplicates_found,
            duplicates_removed=removed_count,
            duplicate_groups=duplicate_groups,
            execution_time=execution_time,
            processed_at=datetime.now(),
        )

    def get_duplicate_statistics(
        self, duplicate_groups: list[DuplicateGroup]
    ) -> dict[str, Any]:
        """获取重复统计信息"""
        total_groups = len(duplicate_groups)
        total_duplicates = sum(len(group.records) for group in duplicate_groups)

        # 统计重复类型分布
        duplicate_types: dict[str, int] = defaultdict(int)
        similarity_scores = []

        for group in duplicate_groups:
            for record in group.records:
                duplicate_types[record.duplicate_type.value] += 1
                similarity_scores.append(record.similarity_score)

        # 计算相似度分布
        similarity_distribution = {
            "min": min(similarity_scores) if similarity_scores else 0,
            "max": max(similarity_scores) if similarity_scores else 0,
            "avg": (
                sum(similarity_scores) / len(similarity_scores)
                if similarity_scores
                else 0
            ),
        }

        return {
            "total_groups": total_groups,
            "total_duplicates": total_duplicates,
            "duplicate_types": dict(duplicate_types),
            "similarity_distribution": similarity_distribution,
        }

    def find_database_duplicates(
        self,
        table_name: str = "daily_stock_metrics",
        date_range: Union[tuple[str, str], None] = None,
    ) -> list[DuplicateGroup]:
        """查找数据库中的重复记录

        Args:
            table_name: 表名
            date_range: 日期范围 (start_date, end_date)

        Returns:
            List[DuplicateGroup]: 重复组列表
        """
        query = self.db_session.query(DailyStockMetrics)

        if date_range:
            start_date_str, end_date_str = date_range
            from datetime import datetime

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            query = query.filter(
                and_(
                    DailyStockMetrics.date >= start_date,
                    DailyStockMetrics.date <= end_date,
                )
            )

        # 查找具有相同 code + date 的记录
        records = query.all()

        # 按 code + date 分组
        groups = defaultdict(list)
        for record in records:
            key = f"{record.code}_{record.date}"
            groups[key].append(record)

        # 识别重复组
        duplicate_groups = []
        for key, group_records in groups.items():
            if len(group_records) > 1:
                duplicate_records = []
                for record in group_records:
                    duplicate_record = DuplicateRecord(
                        duplicate_type=DuplicateType.EXACT,
                        similarity_score=1.0,
                        record_id=record.id,
                        conflicting_fields=[],
                        data_source=record.data_source or "unknown",  # type: ignore
                        quality_score=record.quality_score or 0.0,  # type: ignore
                        created_at=record.updated_at or datetime.now(),
                    )
                    duplicate_records.append(duplicate_record)

                duplicate_group = DuplicateGroup(
                    primary_key=key,
                    records=duplicate_records,
                    recommended_action=DeduplicationStrategy.KEEP_HIGHEST_QUALITY,
                    confidence=0.9,
                )
                duplicate_groups.append(duplicate_group)

        return duplicate_groups

    def find_duplicates_in_list(
        self,
        data_list: list[dict[str, Any]],
        unique_fields: Union[list[str], None] = None,
    ) -> list[DuplicateGroup]:
        """在数据列表中查找重复项

        Args:
            data_list: 数据列表
            unique_fields: 用于判断重复的字段列表，默认为 ['code', 'date']

        Returns:
            List[DuplicateGroup]: 重复组列表
        """
        if unique_fields is None:
            unique_fields = ["code", "date"]

        # 按唯一字段分组
        groups = defaultdict(list)
        for i, data in enumerate(data_list):
            # 构建唯一键
            key_parts = []
            for field in unique_fields:
                value = data.get(field, "")
                key_parts.append(str(value))
            key = "_".join(key_parts)

            # 添加索引信息
            data_with_index = data.copy()
            data_with_index["_list_index"] = i
            groups[key].append(data_with_index)

        # 识别重复组
        duplicate_groups = []
        for key, group_records in groups.items():
            if len(group_records) > 1:
                duplicate_records = []
                # 以第一条记录为基准，计算其他记录的相似度
                base_record = group_records[0]
                for i, record in enumerate(group_records):
                    if i == 0:
                        # 第一条记录作为基准
                        similarity_score = 1.0
                        duplicate_type = DuplicateType.EXACT
                    else:
                        # 计算与基准记录的相似度
                        similarity_score = self._calculate_similarity(
                            base_record, record
                        )
                        duplicate_type = self._determine_duplicate_type(
                            similarity_score
                        )

                    duplicate_record = DuplicateRecord(
                        duplicate_type=duplicate_type,
                        similarity_score=similarity_score,
                        record_id=record.get("_list_index", 0),
                        conflicting_fields=[],
                        data_source=record.get("data_source", "unknown"),
                        quality_score=record.get("quality_score", 0.0),
                        created_at=datetime.now(),
                        index=record.get("_list_index", 0),
                        data=record,
                    )
                    duplicate_records.append(duplicate_record)

                duplicate_group = DuplicateGroup(
                    primary_key=key,
                    records=duplicate_records,
                    recommended_action=DeduplicationStrategy.KEEP_FIRST,
                    confidence=0.9,
                )
                duplicate_groups.append(duplicate_group)

        return duplicate_groups

    def batch_deduplicate_data(
        self,
        data_list: list[dict[str, Any]],
        strategy: DeduplicationStrategy = DeduplicationStrategy.KEEP_HIGHEST_QUALITY,
        unique_fields: Union[list[str], None] = None,
    ) -> DeduplicationReport:
        """批量去重数据

        Args:
            data_list: 待去重的数据列表
            strategy: 去重策略
            unique_fields: 用于判断重复的字段列表，默认为['code', 'date']

        Returns:
            去重报告
        """
        if not data_list:
            return DeduplicationReport(
                total_processed=0,
                duplicates_found=0,
                duplicates_removed=0,
                duplicate_groups=[],
                execution_time=0.0,
                processed_at=datetime.now(),
            )

        if unique_fields is None:
            unique_fields = ["code", "date"]

        # 查找重复项
        duplicate_groups = self.find_duplicates_in_list(data_list, unique_fields)

        if not duplicate_groups:
            return DeduplicationReport(
                total_processed=len(data_list),
                duplicates_found=0,
                duplicates_removed=0,
                duplicate_groups=[],
                execution_time=0.0,
                processed_at=datetime.now(),
            )

        # 记录要删除的索引
        indices_to_remove = set()

        for group in duplicate_groups:
            if strategy == DeduplicationStrategy.KEEP_FIRST:
                # 保留第一个，删除其他
                for i in range(1, len(group.records)):
                    indices_to_remove.add(group.records[i].record_id)
            elif strategy == DeduplicationStrategy.KEEP_LAST:
                # 保留最后一个，删除其他
                for i in range(len(group.records) - 1):
                    indices_to_remove.add(group.records[i].record_id)
            elif strategy == DeduplicationStrategy.KEEP_HIGHEST_QUALITY:
                # 保留质量最高的，删除其他
                best_record = max(group.records, key=lambda r: r.quality_score)
                for record in group.records:
                    if record.record_id != best_record.record_id:
                        indices_to_remove.add(record.record_id)

        # 构建去重后的数据列表
        deduplicated_data = []
        for i, data in enumerate(data_list):
            if i not in indices_to_remove:
                deduplicated_data.append(data)

        duplicates_found = sum(len(group.records) for group in duplicate_groups)
        duplicates_removed = len(indices_to_remove)

        self.logger.info(
            f"批量去重完成: 原始数据 {len(data_list)} 条，去重后 {len(deduplicated_data)} 条"
        )

        report = DeduplicationReport(
            total_processed=len(data_list),
            duplicates_found=duplicates_found,
            duplicates_removed=duplicates_removed,
            duplicate_groups=duplicate_groups,
            execution_time=0.0,  # 可以后续添加时间计算
            processed_at=datetime.now(),
        )

        # 为了向后兼容，将去重后的数据存储在报告中
        report.deduplicated_data = deduplicated_data

        return report

    def remove_database_duplicates(
        self,
        duplicate_groups: list[DuplicateGroup],
        strategy: DeduplicationStrategy = DeduplicationStrategy.KEEP_HIGHEST_QUALITY,
    ) -> int:
        """删除数据库中的重复记录

        Args:
            duplicate_groups: 重复组列表
            strategy: 去重策略

        Returns:
            int: 删除的记录数
        """
        removed_count = 0

        try:
            for group in duplicate_groups:
                # 确定要保留的记录
                keep_record = self._select_record_to_keep(group.records, strategy)

                # 删除其他记录
                for record in group.records:
                    if record.record_id != keep_record.record_id:
                        db_record = (
                            self.db_session.query(DailyStockMetrics)
                            .filter(DailyStockMetrics.id == record.record_id)
                            .first()
                        )

                        if db_record:
                            # 标记为重复而非直接删除
                            db_record.is_duplicate = True  # type: ignore
                            db_record.duplicate_source = keep_record.data_source  # type: ignore
                            removed_count += 1

                            # 记录去重日志
                            self._log_deduplication_action(
                                record.record_id,
                                "daily_stock_metrics",
                                f"标记为重复，保留记录ID: {keep_record.record_id}",
                            )

                # 更新保留记录的状态
                keep_db_record = (
                    self.db_session.query(DailyStockMetrics)
                    .filter(DailyStockMetrics.id == keep_record.record_id)
                    .first()
                )

                if keep_db_record:
                    keep_db_record.is_duplicate = False  # type: ignore
                    keep_db_record.duplicate_source = None  # type: ignore

            self.db_session.commit()

        except Exception as e:
            self.logger.error(f"删除重复记录失败: {str(e)}")
            self.db_session.rollback()
            raise

        return removed_count

    def _group_by_unique_key(
        self, data_list: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """按唯一键分组数据"""
        groups = defaultdict(list)

        for data in data_list:
            # 构建唯一键 (code + date)
            code = data.get("code", "")
            date = data.get("date", "")
            unique_key = f"{code}_{date}"

            groups[unique_key].append(data)

        return dict(groups)

    def _analyze_duplicate_group(
        self, key: str, records: list[dict[str, Any]]
    ) -> DuplicateGroup:
        """分析重复组"""
        duplicate_records = []

        for i, record in enumerate(records):
            # 计算与第一条记录的相似度
            similarity_score = self._calculate_similarity(records[0], record)

            # 确定重复类型
            duplicate_type = self._determine_duplicate_type(similarity_score)

            # 识别冲突字段
            conflicting_fields = self._find_conflicting_fields(records[0], record)

            duplicate_record = DuplicateRecord(
                duplicate_type=duplicate_type,
                similarity_score=similarity_score,
                record_id=i,  # 临时ID
                conflicting_fields=conflicting_fields,
                data_source=record.get("data_source", "unknown"),
                quality_score=record.get("quality_score", 0.0),
                created_at=datetime.now(),
                index=i,
                data=record,
            )
            duplicate_records.append(duplicate_record)

        # 推荐去重策略
        recommended_action = self._recommend_strategy(duplicate_records)

        return DuplicateGroup(
            primary_key=key,
            records=duplicate_records,
            recommended_action=recommended_action,
            confidence=0.8,
        )

    def _calculate_similarity(
        self, record1: dict[str, Any], record2: dict[str, Any]
    ) -> float:
        """计算两条记录的相似度"""
        if record1 == record2:
            return 1.0

        total_weight = 0.0
        weighted_similarity = 0.0

        for field, weight in self.field_weights.items():
            if field in record1 and field in record2:
                field_similarity = self._calculate_field_similarity(
                    record1[field], record2[field], field
                )
                weighted_similarity += field_similarity * weight
                total_weight += weight

        return weighted_similarity / total_weight if total_weight > 0 else 0.0

    def _calculate_field_similarity(
        self, value1: Any, value2: Any, field_name: str
    ) -> float:
        """计算字段相似度"""
        if value1 == value2:
            return 1.0

        if value1 is None or value2 is None:
            return 0.0

        # 数值字段相似度计算
        if field_name in ["open", "high", "low", "close", "volume"]:
            try:
                v1, v2 = float(value1), float(value2)
                if v1 == 0 and v2 == 0:
                    return 1.0
                if v1 == 0 or v2 == 0:
                    return 0.0

                # 计算相对差异
                relative_diff = abs(v1 - v2) / max(abs(v1), abs(v2))
                return max(0.0, 1.0 - relative_diff)
            except (ValueError, TypeError):
                return 0.0

        # 字符串字段相似度
        str1, str2 = str(value1), str(value2)
        if str1 == str2:
            return 1.0

        # 简单的字符串相似度 (可以使用更复杂的算法如编辑距离)
        common_chars = set(str1) & set(str2)
        total_chars = set(str1) | set(str2)

        return len(common_chars) / len(total_chars) if total_chars else 0.0

    def _determine_duplicate_type(self, similarity_score: float) -> DuplicateType:
        """确定重复类型"""
        if similarity_score >= self.similarity_thresholds["exact"]:
            return DuplicateType.EXACT
        elif similarity_score >= self.similarity_thresholds["partial"]:
            return DuplicateType.PARTIAL
        elif similarity_score >= self.similarity_thresholds["similar"]:
            return DuplicateType.SIMILAR
        else:
            return DuplicateType.PARTIAL  # 默认为部分重复

    def _find_conflicting_fields(
        self, record1: dict[str, Any], record2: dict[str, Any]
    ) -> list[str]:
        """查找冲突字段"""
        conflicting_fields = []

        common_fields = set(record1.keys()) & set(record2.keys())
        for field in common_fields:
            if record1[field] != record2[field]:
                conflicting_fields.append(field)

        return conflicting_fields

    def _recommend_strategy(
        self, records: list[DuplicateRecord]
    ) -> DeduplicationStrategy:
        """推荐去重策略"""
        # 如果所有记录都是完全重复，保留第一条
        if all(r.duplicate_type == DuplicateType.EXACT for r in records):
            return DeduplicationStrategy.KEEP_FIRST

        # 如果有质量评分差异，保留质量最高的
        quality_scores = [r.quality_score for r in records]
        if max(quality_scores) - min(quality_scores) > 0.1:
            return DeduplicationStrategy.KEEP_HIGHEST_QUALITY

        # 默认保留最新的
        return DeduplicationStrategy.KEEP_LAST

    def _apply_deduplication_strategy(
        self, group: DuplicateGroup, strategy: DeduplicationStrategy
    ) -> int:
        """应用去重策略"""
        if len(group.records) <= 1:
            return 0

        keep_record = self._select_record_to_keep(group.records, strategy)

        # 标记其他记录为重复
        removed_count = 0
        for record in group.records:
            if record.record_id != keep_record.record_id:
                # 这里只是标记，实际的数据库操作在其他方法中进行
                removed_count += 1

        return removed_count

    def _select_record_to_keep(
        self, records: list[DuplicateRecord], strategy: DeduplicationStrategy
    ) -> DuplicateRecord:
        """选择要保留的记录"""
        if strategy == DeduplicationStrategy.KEEP_FIRST:
            return min(records, key=lambda r: r.created_at or datetime.min)
        elif strategy == DeduplicationStrategy.KEEP_LAST:
            return max(records, key=lambda r: r.created_at or datetime.min)
        elif strategy == DeduplicationStrategy.KEEP_HIGHEST_QUALITY:
            return max(records, key=lambda r: r.quality_score)
        else:
            # 默认保留质量最高的
            return max(records, key=lambda r: r.quality_score)

    def _log_deduplication_action(
        self, record_id: int, table_name: str, message: str
    ) -> None:
        """记录去重操作日志"""
        try:
            log_entry = DataQualityLog(
                record_id=record_id,
                table_name=table_name,
                operation_type="deduplication",
                status="success",
                message=message,
                execution_time=0.0,
            )

            self.db_session.add(log_entry)
            # 注意：这里不提交，由调用方统一提交

        except Exception as e:
            self.logger.error(f"记录去重日志失败: {str(e)}")

    def generate_duplicate_hash(
        self,
        data: Union[dict[str, Any], None] = None,
        fields: Union[list[str], None] = None,
    ) -> str:
        """生成数据哈希值用于快速重复检测

        Args:
            data: 数据字典
            fields: 参与哈希计算的字段列表，默认使用关键字段

        Returns:
            str: 哈希值
        """
        if data is None:
            return ""

        if fields is None:
            fields = ["code", "date", "close", "volume"]

        # 构建哈希字符串
        hash_parts = []
        for field in sorted(fields):  # 排序确保一致性
            if field in data:
                value = data[field]
                if isinstance(value, float):
                    # 浮点数保留4位小数避免精度问题
                    hash_parts.append(f"{field}:{value:.4f}")
                else:
                    hash_parts.append(f"{field}:{value}")

        hash_string = "|".join(hash_parts)
        return hashlib.md5(
            hash_string.encode("utf-8"), usedforsecurity=False
        ).hexdigest()
