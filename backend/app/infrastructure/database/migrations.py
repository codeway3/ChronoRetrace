from __future__ import annotations
from typing import Union

# !/usr/bin/env python3
"""

ChronoRetrace - 数据库迁移模块

本模块提供数据库结构迁移和索引优化的自动化功能。
支持版本化的数据库变更管理，确保生产环境的安全升级。

Author: ChronoRetrace Team
Date: 2024
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .index_optimization import DatabaseIndexOptimizer
from .session import get_db

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """
    数据库迁移管理器

    提供版本化的数据库迁移功能，包括索引创建、表结构变更等。
    """

    def __init__(self):
        """初始化迁移管理器"""
        self.migrations = [
            {
                "version": "001",
                "name": "create_performance_indexes",
                "description": "创建性能优化索引",
                "up": self._migration_001_up,
                "down": self._migration_001_down,
            },
            {
                "version": "002",
                "name": "add_cache_metadata_table",
                "description": "添加缓存元数据表",
                "up": self._migration_002_up,
                "down": self._migration_002_down,
            },
        ]


    def _ensure_migration_table(self, session: Session) -> None:
        """
        确保迁移记录表存在
        """
        try:
            session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER
                )
            """
                )
            )
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"创建迁移表失败: {e}")
            raise


    def _is_migration_applied(self, session: Session, version: str) -> bool:
        """
        检查迁移是否已应用
        """
        try:
            result = session.execute(
                text("SELECT version FROM schema_migrations WHERE version = :version"),
                {"version": version},
            ).fetchone()
            return result is not None
        except Exception:
            return False


    def _record_migration(
        self, session: Session, migration: dict, execution_time_ms: int
    ) -> None:
        """
        记录迁移执行
        """
        try:
            session.execute(
                text(
                    """
                INSERT INTO schema_migrations (version, name, description, execution_time_ms)
                VALUES (:version, :name, :description, :execution_time_ms)
            """
                ),
                {
                    "version": migration["version"],
                    "name": migration["name"],
                    "description": migration["description"],
                    "execution_time_ms": execution_time_ms,
                },
            )
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"记录迁移失败: {e}")
            raise


    def _migration_001_up(self, session: Session) -> None:
        """
        迁移001: 创建性能优化索引
        """
        logger.info("执行迁移001: 创建性能优化索引")

        # 使用索引优化器创建索引
        optimizer = DatabaseIndexOptimizer()
        index_results = optimizer.create_optimized_indexes(session)

        success_count = sum(1 for result in index_results.values() if result)
        logger.info(f"迁移001完成: 成功创建 {success_count} 个索引")


    def _migration_001_down(self, session: Session) -> None:
        """
        回滚迁移001: 删除性能优化索引
        """
        logger.info("回滚迁移001: 删除性能优化索引")

        indexes_to_drop = [
            "idx_daily_metrics_code_date",
            "idx_daily_metrics_market_date",
            "idx_daily_metrics_pe_ratio_range",
            "idx_daily_metrics_market_cap_range",
            "idx_daily_metrics_updated_at",
            "idx_stock_data_ts_code_date_interval",
        ]

        for index_name in indexes_to_drop:
            try:
                session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                logger.info(f"删除索引: {index_name}")
            except Exception as e:
                logger.warning(f"删除索引失败 {index_name}: {e}")

        session.commit()


    def _migration_002_up(self, session: Session) -> None:
        """
        迁移002: 添加缓存元数据表
        """
        logger.info("执行迁移002: 添加缓存元数据表")

        # 创建表
        session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS cache_metadata (
                id SERIAL PRIMARY KEY,
                cache_key VARCHAR(255) NOT NULL UNIQUE,
                cache_type VARCHAR(50) NOT NULL,
                data_source VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                hit_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                data_size_bytes INTEGER DEFAULT 0
            )
        """
            )
        )

        # 分别创建索引
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_metadata (cache_key)"
            )
        )
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_metadata (cache_type)"
            )
        )
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_metadata (expires_at)"
            )
        )
        session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_metadata (last_accessed)"
            )
        )

        session.commit()
        logger.info("缓存元数据表创建完成")


    def _migration_002_down(self, session: Session) -> None:
        """
        回滚迁移002: 删除缓存元数据表
        """
        logger.info("回滚迁移002: 删除缓存元数据表")

        session.execute(text("DROP TABLE IF EXISTS cache_metadata"))
        session.commit()


    def migrate_up(self, target_version: Union[str, None] = None) -> dict[str, Any]:
        """
        执行向上迁移

        Args:
            target_version: 目标版本，None表示迁移到最新版本

        Returns:
            Dict: 迁移结果
        """
        migration_result = {
            "start_time": datetime.utcnow(),
            "applied_migrations": [],
            "errors": [],
            "total_execution_time_ms": 0,
        }

        db = next(get_db())
        try:
            # 确保迁移表存在
            self._ensure_migration_table(db)

            # 执行迁移
            for migration in self.migrations:
                # 检查是否需要执行此迁移
                if target_version and migration["version"] > target_version:
                    break

                if self._is_migration_applied(db, migration["version"]):
                    logger.info(f"迁移 {migration['version']} 已应用，跳过")
                    continue

                # 执行迁移
                start_time = datetime.utcnow()
                try:
                    migration["up"](db)
                    end_time = datetime.utcnow()
                    execution_time_ms = int(
                        (end_time - start_time).total_seconds() * 1000
                    )

                    # 记录迁移
                    self._record_migration(db, migration, execution_time_ms)

                    migration_result["applied_migrations"].append(
                        {
                            "version": migration["version"],
                            "name": migration["name"],
                            "execution_time_ms": execution_time_ms,
                        }
                    )
                    migration_result["total_execution_time_ms"] += execution_time_ms

                    logger.info(
                        f"迁移 {migration['version']} 执行成功，耗时 {execution_time_ms}ms"
                    )

                except Exception as e:
                    error_msg = f"迁移 {migration['version']} 执行失败: {e}"
                    migration_result["errors"].append(error_msg)
                    logger.error(error_msg)
                    raise

            migration_result["end_time"] = datetime.utcnow()
            migration_result["success"] = len(migration_result["errors"]) == 0

            return migration_result

        except Exception as e:
            migration_result["errors"].append(str(e))
            migration_result["success"] = False
            logger.error(f"迁移过程失败: {e}")
            raise
        finally:
            db.close()


    def get_migration_status(self) -> dict[str, Any]:
        """
        获取迁移状态

        Returns:
            Dict: 迁移状态信息
        """
        status: dict[str, Any] = {
            "available_migrations": [],
            "applied_migrations": [],
            "pending_migrations": [],
        }

        db = next(get_db())
        try:
            self._ensure_migration_table(db)

            # 获取已应用的迁移
            applied_result = db.execute(
                text(
                    "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
                )
            ).fetchall()

            applied_versions = set()
            for row in applied_result:
                status["applied_migrations"].append(
                    {"version": row[0], "name": row[1], "applied_at": row[2]}
                )
                applied_versions.add(row[0])

            # 分析可用和待执行的迁移
            for migration in self.migrations:
                status["available_migrations"].append(
                    {
                        "version": migration["version"],
                        "name": migration["name"],
                        "description": migration["description"],
                    }
                )

                if migration["version"] not in applied_versions:
                    status["pending_migrations"].append(
                        {
                            "version": migration["version"],
                            "name": migration["name"],
                            "description": migration["description"],
                        }
                    )

            return status

        except Exception as e:
            logger.error(f"获取迁移状态失败: {e}")
            return {"error": str(e)}
        finally:
            db.close()


# 全局迁移管理器实例
db_migration = DatabaseMigration()


def run_database_migrations(target_version: Union[str, None] = None) -> dict[str, Any]:
    """
    执行数据库迁移的便捷函数

    Args:
        target_version: 目标版本

    Returns:
        Dict: 迁移结果
    """
    return db_migration.migrate_up(target_version)


def get_database_migration_status() -> dict[str, Any]:
    """
    获取数据库迁移状态的便捷函数

    Returns:
        Dict: 迁移状态
    """
    return db_migration.get_migration_status()


if __name__ == "__main__":
    # 命令行执行迁移
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--migrate":
            target = sys.argv[2] if len(sys.argv) > 2 else None
            print(f"开始数据库迁移到版本: {target or '最新'}")
            result = run_database_migrations(target)
            print(f"迁移结果: {result}")
        elif sys.argv[1] == "--status":
            print("获取迁移状态...")
            status = get_database_migration_status()
            print(f"迁移状态: {status}")
    else:
        print("用法: python migrations.py [--migrate [version] | --status]")
