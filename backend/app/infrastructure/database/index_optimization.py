#!/usr/bin/env python3
"""
ChronoRetrace - 数据库索引优化模块

本模块实现数据库索引的优化策略，特别针对DailyStockMetrics表的查询性能优化。
根据enhance_plan.md中的性能优化要求，提供索引创建、分析和维护功能。

Author: ChronoRetrace Team
Date: 2024
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .models import DailyStockMetrics
from .session import get_db_engine, get_db_session

logger = logging.getLogger(__name__)


class DatabaseIndexOptimizer:
    """
    数据库索引优化器

    提供数据库索引的创建、分析、优化和维护功能，
    特别针对股票数据查询的性能优化。
    """

    def __init__(self, engine: Engine | None = None):
        """初始化索引优化器"""
        self.engine = engine or get_db_engine()
        self.optimization_history: list[dict] = []

    def analyze_query_patterns(self, session: Session) -> dict[str, Any]:
        """
        分析查询模式，识别需要优化的查询

        Returns:
            Dict: 查询分析结果
        """
        try:
            analysis_result: dict[str, Any] = {
                "table_stats": {},
                "query_patterns": [],
                "recommendations": [],
            }

            # 分析DailyStockMetrics表统计信息
            metrics_count = session.query(DailyStockMetrics).count()
            analysis_result["table_stats"]["daily_stock_metrics"] = {
                "total_records": metrics_count,
                "estimated_size_mb": metrics_count * 0.5 / 1024,  # 估算大小
            }

            # 分析常见查询模式
            common_patterns = [
                {
                    "pattern": "按股票代码和日期范围查询",
                    "frequency": "高",
                    "columns": ["code", "date"],
                    "index_needed": "composite_code_date",
                },
                {
                    "pattern": "按市场和日期查询",
                    "frequency": "中",
                    "columns": ["market", "date"],
                    "index_needed": "composite_market_date",
                },
                {
                    "pattern": "按PE比率范围筛选",
                    "frequency": "中",
                    "columns": ["pe_ratio"],
                    "index_needed": "pe_ratio_range",
                },
                {
                    "pattern": "按市值范围筛选",
                    "frequency": "中",
                    "columns": ["market_cap"],
                    "index_needed": "market_cap_range",
                },
            ]

            analysis_result["query_patterns"] = common_patterns

            # 生成优化建议
            if metrics_count > 100000:  # 大表优化建议
                analysis_result["recommendations"].extend(
                    [
                        "创建复合索引 (code, date) 优化时间序列查询",
                        "创建复合索引 (market, date) 优化市场级别查询",
                        "考虑按日期分区以提升查询性能",
                        "创建部分索引优化筛选查询",
                    ]
                )

            logger.info(f"查询模式分析完成，发现 {len(common_patterns)} 种常见模式")
            return analysis_result

        except Exception as e:
            logger.error(f"查询模式分析失败: {e}")
            raise

    def create_optimized_indexes(self, session: Session) -> dict[str, bool]:
        """
        创建优化的索引

        Returns:
            Dict[str, bool]: 索引创建结果
        """
        results: dict[str, bool] = {}

        # 定义需要创建的索引
        indexes_to_create = [
            {
                "name": "idx_daily_metrics_code_date",
                "table": "daily_stock_metrics",
                "columns": ["code", "date"],
                "description": "股票代码和日期复合索引，优化时间序列查询",
            },
            {
                "name": "idx_daily_metrics_market_date",
                "table": "daily_stock_metrics",
                "columns": ["market", "date"],
                "description": "市场和日期复合索引，优化市场级别查询",
            },
            {
                "name": "idx_daily_metrics_pe_ratio_range",
                "table": "daily_stock_metrics",
                "columns": ["pe_ratio"],
                "description": "PE比率索引，优化估值筛选查询",
                "condition": "pe_ratio IS NOT NULL AND pe_ratio > 0",
            },
            {
                "name": "idx_daily_metrics_market_cap_range",
                "table": "daily_stock_metrics",
                "columns": ["market_cap"],
                "description": "市值索引，优化市值筛选查询",
                "condition": "market_cap IS NOT NULL AND market_cap > 0",
            },
            {
                "name": "idx_daily_metrics_updated_at",
                "table": "daily_stock_metrics",
                "columns": ["updated_at"],
                "description": "更新时间索引，优化增量同步查询",
            },
            {
                "name": "idx_stock_data_ts_code_date_interval",
                "table": "stock_data",
                "columns": ["ts_code", "trade_date", "interval"],
                "description": "股票数据复合索引，优化多维度查询",
            },
        ]

        for index_config in indexes_to_create:
            try:
                result = self._create_index(session, index_config)
                results[index_config["name"]] = result

                if result:
                    logger.info(
                        f"索引创建成功: {index_config['name']} - {index_config['description']}"
                    )
                else:
                    logger.warning(f"索引创建跳过: {index_config['name']} (可能已存在)")

            except Exception as e:
                logger.error(f"索引创建失败: {index_config['name']} - {e}")
                results[index_config["name"]] = False

        # 记录优化历史
        self.optimization_history.append(
            {
                "timestamp": datetime.utcnow(),
                "operation": "create_indexes",
                "results": results,
                "success_count": sum(1 for r in results.values() if r),
            }
        )

        return results

    def _create_index(self, session: Session, index_config: dict) -> bool:
        """
        创建单个索引

        Args:
            session: 数据库会话
            index_config: 索引配置

        Returns:
            bool: 创建是否成功
        """
        try:
            # 检查索引是否已存在
            if self._index_exists(session, index_config["name"]):
                return False

            # 构建CREATE INDEX语句
            columns_str = ", ".join(index_config["columns"])

            if "condition" in index_config:
                # 部分索引
                sql = f"""
                CREATE INDEX {index_config["name"]}
                ON {index_config["table"]} ({columns_str})
                WHERE {index_config["condition"]}
                """
            else:
                # 普通索引
                sql = f"""
                CREATE INDEX {index_config["name"]}
                ON {index_config["table"]} ({columns_str})
                """

            session.execute(text(sql))
            session.commit()
            return True

        except SQLAlchemyError as e:
            session.rollback()
            if "already exists" in str(e).lower():
                return False
            raise

    def _index_exists(self, session: Session, index_name: str) -> bool:
        """
        检查索引是否存在

        Args:
            session: 数据库会话
            index_name: 索引名称

        Returns:
            bool: 索引是否存在
        """
        try:
            # SQLite查询索引存在性
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=:name"
                ),
                {"name": index_name},
            ).fetchone()
            return result is not None
        except Exception:
            return False

    def analyze_index_usage(self, session: Session) -> dict[str, Any]:
        """
        分析索引使用情况

        Returns:
            Dict: 索引使用分析结果
        """
        try:
            analysis: dict[str, Any] = {
                "existing_indexes": [],
                "usage_stats": {},
                "recommendations": [],
            }

            # 获取现有索引信息
            indexes_result = session.execute(
                text("""
                SELECT name, tbl_name, sql
                FROM sqlite_master
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY tbl_name, name
                """)
            ).fetchall()

            for row in indexes_result:
                analysis["existing_indexes"].append(
                    {"name": row[0], "table": row[1], "definition": row[2]}
                )

            # 分析表大小和查询复杂度
            tables_to_analyze = [
                "daily_stock_metrics",
                "stock_data",
                "fundamental_data",
            ]

            for table in tables_to_analyze:
                try:
                    count_result = session.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar()

                    if count_result is not None:
                        analysis["usage_stats"][table] = {
                            "record_count": count_result,
                            "needs_optimization": count_result > 50000,
                        }

                        if count_result > 100000:
                            analysis["recommendations"].append(
                                f"表 {table} 记录数较大({count_result})，建议考虑分区策略"
                            )



                except Exception as e:
                    logger.warning(f"无法分析表 {table}: {e}")

            return analysis

        except Exception as e:
            logger.error(f"索引使用分析失败: {e}")
            raise

    def optimize_database(self, session: Session) -> dict[str, Any]:
        """
        执行完整的数据库优化

        Returns:
            Dict: 优化结果报告
        """
        optimization_report = {
            "start_time": datetime.utcnow(),
            "steps_completed": [],
            "errors": [],
            "performance_improvement": {},
        }

        try:
            # 步骤1: 分析查询模式
            logger.info("开始查询模式分析...")
            query_analysis = self.analyze_query_patterns(session)
            optimization_report["steps_completed"].append("query_pattern_analysis")
            optimization_report["query_analysis"] = query_analysis

            # 步骤2: 创建优化索引
            logger.info("开始创建优化索引...")
            index_results = self.create_optimized_indexes(session)
            optimization_report["steps_completed"].append("index_creation")
            optimization_report["index_results"] = index_results

            # 步骤3: 分析索引使用情况
            logger.info("开始索引使用分析...")
            usage_analysis = self.analyze_index_usage(session)
            optimization_report["steps_completed"].append("index_usage_analysis")
            optimization_report["usage_analysis"] = usage_analysis

            # 步骤4: 执行VACUUM优化
            logger.info("执行数据库VACUUM优化...")
            session.execute(text("VACUUM"))
            session.commit()
            optimization_report["steps_completed"].append("vacuum_optimization")

            # 步骤5: 更新统计信息
            logger.info("更新数据库统计信息...")
            session.execute(text("ANALYZE"))
            session.commit()
            optimization_report["steps_completed"].append("statistics_update")

            optimization_report["end_time"] = datetime.utcnow()
            optimization_report["duration_seconds"] = (
                optimization_report["end_time"] - optimization_report["start_time"]
            ).total_seconds()

            logger.info(
                f"数据库优化完成，耗时 {optimization_report['duration_seconds']:.2f} 秒"
            )

        except Exception as e:
            optimization_report["errors"].append(str(e))
            logger.error(f"数据库优化过程中出现错误: {e}")
            raise

        return optimization_report

    def get_optimization_recommendations(self, session: Session) -> list[str]:
        """
        获取数据库优化建议

        Returns:
            List[str]: 优化建议列表
        """
        recommendations = []

        try:
            # 分析表大小
            metrics_count = session.query(DailyStockMetrics).count()

            if metrics_count > 1000000:
                recommendations.extend(
                    [
                        "考虑实施表分区策略，按日期或股票代码分区",
                        "考虑迁移到PostgreSQL以获得更好的性能",
                        "实施数据归档策略，定期清理历史数据",
                    ]
                )
            elif metrics_count > 100000:
                recommendations.extend(
                    [
                        "创建复合索引优化常见查询",
                        "考虑实施查询结果缓存",
                        "定期执行VACUUM和ANALYZE优化",
                    ]
                )

            # 检查索引覆盖情况
            existing_indexes = self.analyze_index_usage(session)
            index_count = len(existing_indexes["existing_indexes"])

            if index_count < 5:
                recommendations.append("当前索引数量较少，建议创建更多针对性索引")

            return recommendations

        except Exception as e:
            logger.error(f"获取优化建议失败: {e}")
            return ["无法分析当前数据库状态，请检查数据库连接"]


# 全局优化器实例
db_optimizer = DatabaseIndexOptimizer()


def optimize_database_indexes() -> dict[str, Any]:
    """
    执行数据库索引优化的便捷函数

    Returns:
        Dict: 优化结果报告
    """
    with get_db_session() as session:
        return db_optimizer.optimize_database(session)


def get_database_optimization_status() -> dict[str, Any]:
    """
    获取数据库优化状态

    Returns:
        Dict: 优化状态信息
    """
    with get_db_session() as session:
        return {
            "query_analysis": db_optimizer.analyze_query_patterns(session),
            "index_usage": db_optimizer.analyze_index_usage(session),
            "recommendations": db_optimizer.get_optimization_recommendations(session),
            "optimization_history": db_optimizer.optimization_history,
        }


if __name__ == "__main__":
    # 命令行执行优化
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "--optimize":
        print("开始数据库索引优化...")
        result = optimize_database_indexes()
        print(f"优化完成: {result}")
    else:
        print("获取优化状态...")
        status = get_database_optimization_status()
        print(f"当前状态: {status}")
