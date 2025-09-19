#!/usr/bin/env python3
"""
PostgreSQL数据库设置脚本

此脚本用于初始化PostgreSQL数据库，包括：
- 创建数据库用户
- 创建数据库
- 设置权限
- 运行迁移
"""

from __future__ import annotations

from typing import Union


import os
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.infrastructure.database.migration_manager import get_migration_manager


def run_command(command, check=True, capture_output=False):
    """运行shell命令"""
    print(f"执行命令: {command}")
    try:
        result = subprocess.run(
            command, shell=True, check=check, capture_output=capture_output, text=True
        )
        if capture_output:
            return result.stdout.strip()
        return True
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if capture_output:
            print(f"错误输出: {e.stderr}")
        return False


def check_postgres_running():
    """检查PostgreSQL是否运行"""
    print("检查PostgreSQL服务状态...")
    result = run_command(
        "pg_isready -h localhost -p 5432", check=False, capture_output=True
    )
    if result:
        print("✅ PostgreSQL服务正在运行")
        return True
    else:
        print("❌ PostgreSQL服务未运行")
        print("请先启动PostgreSQL服务:")
        print("  macOS: brew services start postgresql")
        print("  Ubuntu: sudo systemctl start postgresql")
        print(
            "  Docker: docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres"
        )
        return False


def create_database_and_user(env="development"):
    """创建数据库和用户"""
    print(f"为{env}环境创建数据库和用户...")

    # 根据环境设置数据库配置
    if env == "development":
        db_name = "chronoretrace_dev"
        db_user = "chronoretrace"
        db_password = "chronoretrace_dev"
    elif env == "testing":
        db_name = "chronoretrace_test"
        db_user = "chronoretrace"
        db_password = "chronoretrace_test"
    elif env == "production":
        db_name = "chronoretrace"
        db_user = "chronoretrace"
        db_password = os.getenv("POSTGRES_PASSWORD", "secure_password_here")
    else:
        print(f"未知环境: {env}")
        return False

    # 创建用户
    create_user_sql = f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{db_user}') THEN
            CREATE USER {db_user} WITH PASSWORD '{db_password}';
        END IF;
    END
    $$;
    """

    # 创建数据库
    create_db_sql = f"""
    SELECT 'CREATE DATABASE {db_name} OWNER {db_user}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}')\\gexec
    """

    # 授权
    grant_sql = f"""
    GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};
    ALTER USER {db_user} CREATEDB;
    """

    # 执行SQL命令
    commands = [
        f'psql -h localhost -U postgres -c "{create_user_sql}"',
        f'psql -h localhost -U postgres -c "{create_db_sql}"',
        f'psql -h localhost -U postgres -c "{grant_sql}"',
    ]

    for cmd in commands:
        if not run_command(cmd, check=False):
            print(f"❌ 数据库设置失败")
            return False

    print(f"✅ 数据库 {db_name} 和用户 {db_user} 创建成功")
    return True


def run_migrations():
    """运行数据库迁移"""
    print("运行数据库迁移...")
    try:
        manager = get_migration_manager()
        manager.migrate()
        print("✅ 数据库迁移完成")
        return True
    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        return False


def setup_extensions():
    """设置PostgreSQL扩展"""
    print("设置PostgreSQL扩展...")

    # 从DATABASE_URL解析连接信息
    db_url = settings.DATABASE_URL
    if "postgresql://" in db_url:
        # 提取数据库名
        db_name = db_url.split("/")[-1]
        user_info = db_url.split("@")[0].split("//")[-1]
        user, password = user_info.split(":")

        extensions = [
            'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
            'CREATE EXTENSION IF NOT EXISTS "pg_trgm";',
            'CREATE EXTENSION IF NOT EXISTS "btree_gin";',
        ]

        for ext in extensions:
            cmd = f'PGPASSWORD={password} psql -h localhost -U {user} -d {db_name} -c "{ext}"'
            run_command(cmd, check=False)

        print("✅ PostgreSQL扩展设置完成")
        return True
    else:
        print("⚠️ 非PostgreSQL数据库，跳过扩展设置")
        return True


def main():
    """主函数"""
    print("ChronoRetrace PostgreSQL数据库设置")
    print("=" * 50)

    # 检查参数
    env = sys.argv[1] if len(sys.argv) > 1 else "development"
    if env not in ["development", "testing", "production"]:
        print(
            "用法: python setup_postgres.py [Union[Union[development, testing], production]]"
        )
        sys.exit(1)

    print(f"设置环境: {env}")

    # 检查PostgreSQL服务
    if not check_postgres_running():
        sys.exit(1)

    # 创建数据库和用户
    if not create_database_and_user(env):
        sys.exit(1)

    # 设置扩展
    if not setup_extensions():
        print("⚠️ 扩展设置失败，但可以继续")

    # 运行迁移
    if not run_migrations():
        sys.exit(1)

    print("\n🎉 PostgreSQL数据库设置完成！")
    print(f"数据库连接URL: {settings.DATABASE_URL}")
    print("\n下一步:")
    print("1. 启动应用: python start_dev.py")
    print("2. 访问API文档: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
