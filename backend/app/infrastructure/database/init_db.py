"""数据库初始化脚本

用于项目启动时自动执行数据库迁移和初始化操作
"""

import asyncio
import logging

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.infrastructure.database.migration_manager import MigrationManager

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """数据库初始化器"""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.migration_manager = MigrationManager(self.database_url)
        self.engine = create_engine(self.database_url)

    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ 数据库连接正常")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            return False

    def check_database_exists(self) -> bool:
        """检查数据库是否存在"""
        try:
            # 从URL中提取数据库名
            db_name = self.database_url.split('/')[-1].split('?')[0]

            # 创建不包含数据库名的连接URL
            base_url = '/'.join(self.database_url.split('/')[:-1])
            base_engine = create_engine(base_url)

            with base_engine.connect() as conn:
                result = conn.execute(text(
                    f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'"
                ))
                exists = result.fetchone() is not None

            base_engine.dispose()
            return exists

        except Exception as e:
            logger.warning(f"检查数据库存在性时出错: {e}")
            return True  # 假设存在，继续执行

    def create_database_if_not_exists(self) -> bool:
        """如果数据库不存在则创建"""
        try:
            if self.check_database_exists():
                logger.info("数据库已存在")
                return True

            # 从URL中提取数据库名
            db_name = self.database_url.split('/')[-1].split('?')[0]

            # 创建不包含数据库名的连接URL
            base_url = '/'.join(self.database_url.split('/')[:-1])
            base_engine = create_engine(base_url)

            with base_engine.connect() as conn:
                # 注意：这里需要使用autocommit模式来执行CREATE DATABASE
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()

            base_engine.dispose()
            logger.info(f"✅ 数据库 {db_name} 创建成功")
            return True

        except Exception as e:
            logger.error(f"❌ 创建数据库失败: {e}")
            return False

    def run_migrations(self) -> bool:
        """执行数据库迁移"""
        try:
            logger.info("开始执行数据库迁移...")

            # 获取迁移状态
            status = self.migration_manager.get_migration_status()
            logger.info(f"迁移状态: 总计 {status['total_migrations']} 个，已应用 {status['applied_count']} 个，待执行 {status['pending_count']} 个")

            if status['pending_count'] == 0:
                logger.info("✅ 所有迁移已是最新状态")
                return True

            # 执行迁移
            success = self.migration_manager.migrate()

            if success:
                logger.info("✅ 数据库迁移执行成功")
            else:
                logger.error("❌ 数据库迁移执行失败")

            return success

        except Exception as e:
            logger.error(f"❌ 执行数据库迁移时出错: {e}")
            return False

    def verify_tables(self) -> bool:
        """验证关键表是否存在"""
        required_tables = [
            'users',
            'user_roles',
            'user_sessions',
            'user_activity_logs',
            'user_preferences',
            'user_watchlists',
            'watchlist_stocks'
        ]

        try:
            with self.engine.connect() as conn:
                for table in required_tables:
                    # SQLite使用sqlite_master表查询表信息
                    result = conn.execute(text(
                        f"SELECT COUNT(*) FROM sqlite_master "
                        f"WHERE type='table' AND name='{table}'"
                    ))

                    if result.scalar() == 0:
                        logger.error(f"❌ 关键表 {table} 不存在")
                        return False

            logger.info("✅ 所有关键表验证通过")
            return True

        except Exception as e:
            logger.error(f"❌ 验证表结构时出错: {e}")
            return False

    def initialize(self, force_recreate: bool = False) -> bool:
        """完整的数据库初始化流程"""
        logger.info("开始数据库初始化...")

        try:
            # 1. 检查数据库连接
            if not self.check_database_connection():
                # 尝试创建数据库
                if not self.create_database_if_not_exists():
                    return False

                # 重新检查连接
                if not self.check_database_connection():
                    return False

            # 2. 如果强制重建，先重置数据库
            if force_recreate:
                logger.warning("强制重建模式：正在重置数据库...")
                if not self.migration_manager.reset_database():
                    logger.error("重置数据库失败")
                    return False

            # 3. 执行迁移
            if not self.run_migrations():
                return False

            # 4. 验证表结构
            if not self.verify_tables():
                return False

            logger.info("✅ 数据库初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False
        finally:
            # 清理连接
            self.engine.dispose()

    def get_database_info(self) -> dict:
        """获取数据库信息"""
        try:
            with self.engine.connect() as conn:
                # 获取数据库版本
                version_result = conn.execute(text("SELECT VERSION()"))
                db_version = version_result.scalar()

                # 获取数据库名
                db_name_result = conn.execute(text("SELECT DATABASE()"))
                db_name = db_name_result.scalar()

                # 获取表数量
                table_count_result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"
                ))
                table_count = table_count_result.scalar()

                # 获取迁移状态
                migration_status = self.migration_manager.get_migration_status()

                return {
                    "database_name": db_name,
                    "database_version": db_version,
                    "table_count": table_count,
                    "migration_status": migration_status,
                    "connection_url": self.database_url.replace(
                        self.database_url.split('@')[0].split('//')[-1],
                        "***:***"
                    ) if '@' in self.database_url else self.database_url
                }

        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {"error": str(e)}


# 便捷函数
def initialize_database(force_recreate: bool = False) -> bool:
    """初始化数据库的便捷函数"""
    initializer = DatabaseInitializer()
    return initializer.initialize(force_recreate=force_recreate)


def get_database_info() -> dict:
    """获取数据库信息的便捷函数"""
    initializer = DatabaseInitializer()
    return initializer.get_database_info()


async def async_initialize_database(force_recreate: bool = False) -> bool:
    """异步初始化数据库"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, initialize_database, force_recreate)


if __name__ == "__main__":
    import sys

    force_recreate = "--force" in sys.argv or "-f" in sys.argv

    if "--info" in sys.argv or "-i" in sys.argv:
        # 显示数据库信息
        info = get_database_info()
        print("数据库信息:")
        for key, value in info.items():
            if key == "migration_status" and isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
    else:
        # 执行初始化
        success = initialize_database(force_recreate=force_recreate)
        if success:
            print("✅ 数据库初始化成功")
            sys.exit(0)
        else:
            print("❌ 数据库初始化失败")
            sys.exit(1)
