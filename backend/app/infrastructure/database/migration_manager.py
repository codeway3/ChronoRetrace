"""数据库迁移管理器

提供数据库迁移的统一管理接口，包括：
- 迁移脚本的执行
- 迁移版本的跟踪
- 迁移状态的管理
"""

import importlib.util
import os
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

Base = declarative_base()


class MigrationHistory(Base):
    """迁移历史记录表"""
    __tablename__ = "migration_history"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(String(1000))


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.migrations_dir = os.path.join(
            os.path.dirname(__file__), "migrations"
        )

        # 确保迁移历史表存在
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """确保迁移历史表存在"""
        try:
            MigrationHistory.metadata.create_all(bind=self.engine)
        except Exception as e:
            print(f"创建迁移历史表失败: {e}")

    def get_migration_files(self) -> list[dict[str, str]]:
        """获取所有迁移文件"""
        migrations = []

        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)
            return migrations

        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith(".py") and not filename.startswith("__"):
                # 提取版本号（假设文件名格式为：001_description.py）
                version = filename.split("_")[0]
                name = filename[:-3]  # 移除.py扩展名
                filepath = os.path.join(self.migrations_dir, filename)

                migrations.append({
                    "version": version,
                    "name": name,
                    "filename": filename,
                    "filepath": filepath
                })

        return migrations

    def get_applied_migrations(self) -> list[str]:
        """获取已应用的迁移版本列表"""
        session = self.Session()
        try:
            applied = session.query(MigrationHistory.version).filter(
                MigrationHistory.success
            ).all()
            return [version[0] for version in applied]
        except Exception:
            return []
        finally:
            session.close()

    def get_pending_migrations(self) -> list[dict[str, str]]:
        """获取待执行的迁移"""
        all_migrations = self.get_migration_files()
        applied_versions = set(self.get_applied_migrations())

        pending = []
        for migration in all_migrations:
            if migration["version"] not in applied_versions:
                pending.append(migration)

        return pending

    def load_migration_module(self, filepath: str):
        """动态加载迁移模块"""
        spec = importlib.util.spec_from_file_location("migration", filepath)
        module = importlib.util.module_from_spec(spec)
        if spec and spec.loader:
            spec.loader.exec_module(module)
        else:
            raise ImportError("无法加载迁移模块: spec 或 loader为空")
        return module

    def apply_migration(self, migration: dict[str, str]) -> bool:
        """应用单个迁移"""
        session = self.Session()

        try:
            print(f"正在应用迁移: {migration['name']}")

            # 加载迁移模块
            module = self.load_migration_module(migration["filepath"])

            # 检查是否有upgrade函数
            if not hasattr(module, "upgrade"):
                raise Exception(f"迁移文件 {migration['filename']} 缺少 upgrade 函数")

            # 执行迁移
            module.upgrade(self.engine)

            # 记录迁移历史
            history = MigrationHistory(
                version=migration["version"],
                name=migration["name"],
                success=True
            )
            session.add(history)
            session.commit()

            print(f"✅ 迁移 {migration['name']} 应用成功")

            # 如果有初始化数据函数，执行它
            if hasattr(module, "insert_initial_data"):
                try:
                    module.insert_initial_data(self.engine)
                    print("✅ 初始数据插入完成")
                except Exception as e:
                    print(f"⚠️ 初始数据插入失败: {e}")

            return True

        except Exception as e:
            session.rollback()
            error_msg = str(e)
            print(f"❌ 迁移 {migration['name']} 应用失败: {error_msg}")

            # 记录失败的迁移
            try:
                history = MigrationHistory(
                    version=migration["version"],
                    name=migration["name"],
                    success=False,
                    error_message=error_msg[:1000]  # 限制错误消息长度
                )
                session.add(history)
                session.commit()
            except Exception:
                pass

            return False

        finally:
            session.close()

    def rollback_migration(self, migration: dict[str, str]) -> bool:
        """回滚单个迁移"""
        session = self.Session()

        try:
            print(f"正在回滚迁移: {migration['name']}")

            # 加载迁移模块
            module = self.load_migration_module(migration["filepath"])

            # 检查是否有downgrade函数
            if not hasattr(module, "downgrade"):
                raise Exception(
                    f"迁移文件 {migration['filename']} 缺少 downgrade 函数")

            # 执行回滚
            module.downgrade(self.engine)

            # 删除迁移历史记录
            session.query(MigrationHistory).filter(
                MigrationHistory.version == migration["version"]
            ).delete()
            session.commit()

            print(f"✅ 迁移 {migration['name']} 回滚成功")
            return True

        except Exception as e:
            session.rollback()
            print(f"❌ 迁移 {migration['name']} 回滚失败: {e}")
            return False

        finally:
            session.close()

    def migrate(self, target_version: str = None) -> bool:
        """执行迁移到指定版本（默认为最新版本）"""
        pending_migrations = self.get_pending_migrations()

        if not pending_migrations:
            print("✅ 没有待执行的迁移")
            return True

        # 如果指定了目标版本，只执行到该版本
        if target_version:
            pending_migrations = [
                m for m in pending_migrations
                if m["version"] <= target_version
            ]

        print(f"发现 {len(pending_migrations)} 个待执行的迁移")

        success_count = 0
        for migration in pending_migrations:
            if self.apply_migration(migration):
                success_count += 1
            else:
                print(f"迁移在 {migration['name']} 处停止")
                break

        print(f"完成 {success_count}/{len(pending_migrations)} 个迁移")
        return success_count == len(pending_migrations)

    def rollback(self, target_version: str = None, steps: int = 1) -> bool:
        """回滚迁移"""
        applied_migrations = self.get_applied_migrations()
        all_migrations = self.get_migration_files()

        # 构建版本到迁移的映射
        version_to_migration = {
            m["version"]: m for m in all_migrations
        }

        # 确定要回滚的迁移
        if target_version:
            # 回滚到指定版本
            to_rollback = [
                version for version in applied_migrations
                if version > target_version
            ]
        else:
            # 回滚指定步数
            to_rollback = applied_migrations[-steps:] if steps <= len(
                applied_migrations) else applied_migrations

        if not to_rollback:
            print("✅ 没有需要回滚的迁移")
            return True

        print(f"将回滚 {len(to_rollback)} 个迁移")

        # 按版本倒序回滚
        success_count = 0
        for version in reversed(to_rollback):
            if version in version_to_migration:
                migration = version_to_migration[version]
                if self.rollback_migration(migration):
                    success_count += 1
                else:
                    print(f"回滚在版本 {version} 处停止")
                    break

        print(f"完成 {success_count}/{len(to_rollback)} 个回滚")
        return success_count == len(to_rollback)

    def get_migration_status(self) -> dict:
        """获取迁移状态"""
        all_migrations = self.get_migration_files()
        applied_migrations = self.get_applied_migrations()
        pending_migrations = self.get_pending_migrations()

        return {
            "total_migrations": len(all_migrations),
            "applied_count": len(applied_migrations),
            "pending_count": len(pending_migrations),
            "applied_versions": applied_migrations,
            "pending_migrations": [m["name"] for m in pending_migrations],
            "current_version": applied_migrations[-1] if applied_migrations else None
        }

    def reset_database(self) -> bool:
        """重置数据库（删除所有表）"""
        try:
            print("⚠️ 正在重置数据库...")

            # 获取所有表名
            with self.engine.connect() as conn:
                # 禁用外键约束检查（MySQL）
                try:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                except Exception:
                    pass

                # 获取所有表
                result = conn.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE()"
                ))
                tables = [row[0] for row in result]

                # 删除所有表
                for table in tables:
                    try:
                        conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
                    except Exception as e:
                        print(f"删除表 {table} 失败: {e}")

                # 重新启用外键约束检查
                try:
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                except Exception:
                    pass

                conn.commit()

            print("✅ 数据库重置完成")

            # 重新创建迁移历史表
            self._ensure_migration_table()

            return True

        except Exception as e:
            print(f"❌ 数据库重置失败: {e}")
            return False

    def create_migration(self, name: str, description: str = "") -> str:
        """创建新的迁移文件模板"""
        # 获取下一个版本号
        existing_migrations = self.get_migration_files()
        if existing_migrations:
            last_version = max(int(m["version"]) for m in existing_migrations)
            next_version = f"{last_version + 1:03d}"
        else:
            next_version = "001"

        # 生成文件名
        filename = f"{next_version}_{name.lower().replace(' ', '_')}.py"
        filepath = os.path.join(self.migrations_dir, filename)

        # 生成迁移文件模板
        template = f'''"""迁移: {name}

版本: {next_version}
创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
描述: {description}
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


def upgrade(engine):
    """执行数据库升级"""
    # 在这里添加你的升级逻辑
    # 例如：
    # Base.metadata.create_all(bind=engine)

    print(f"✅ 迁移 {next_version} 升级完成")


def downgrade(engine):
    """执行数据库降级"""
    # 在这里添加你的降级逻辑
    # 例如：
    # Base.metadata.drop_all(bind=engine)

    print(f"✅ 迁移 {next_version} 降级完成")


def insert_initial_data(engine):
    """插入初始数据（可选）"""
    # 在这里添加初始数据插入逻辑
    pass
'''

        # 确保目录存在
        os.makedirs(self.migrations_dir, exist_ok=True)

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)

        print(f"✅ 迁移文件已创建: {filename}")
        return filepath


# 便捷函数
def get_migration_manager() -> MigrationManager:
    """获取迁移管理器实例"""
    return MigrationManager()


if __name__ == "__main__":
    # 命令行接口
    import sys

    manager = get_migration_manager()

    if len(sys.argv) < 2:
        print("用法: python migration_manager.py <command> [args]")
        print("命令:")
        print("  status    - 显示迁移状态")
        print("  migrate   - 执行所有待执行的迁移")
        print("  rollback [steps] - 回滚指定步数的迁移")
        print("  reset     - 重置数据库")
        print("  create <name> [description] - 创建新的迁移文件")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        status = manager.get_migration_status()
        print("迁移状态:")
        print(f"  总迁移数: {status['total_migrations']}")
        print(f"  已应用: {status['applied_count']}")
        print(f"  待执行: {status['pending_count']}")
        print(f"  当前版本: {status['current_version'] or '无'}")
        if status['pending_migrations']:
            print(f"  待执行迁移: {', '.join(status['pending_migrations'])}")

    elif command == "migrate":
        manager.migrate()

    elif command == "rollback":
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        manager.rollback(steps=steps)

    elif command == "reset":
        confirm = input("确定要重置数据库吗？这将删除所有数据！(yes/no): ")
        if confirm.lower() == "yes":
            manager.reset_database()
        else:
            print("操作已取消")

    elif command == "create":
        if len(sys.argv) < 3:
            print("请提供迁移名称")
            sys.exit(1)

        name = sys.argv[2]
        description = sys.argv[3] if len(sys.argv) > 3 else ""
        manager.create_migration(name, description)

    else:
        print(f"未知命令: {command}")
        sys.exit(1)
