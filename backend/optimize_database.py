#!/usr/bin/env python3
"""
ChronoRetrace - 数据库优化管理脚本

本脚本提供数据库性能优化的统一入口，包括索引优化、迁移执行等功能。
可以通过命令行参数执行不同的优化操作。

Author: ChronoRetrace Team
Date: 2024
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.database.index_optimization import (
    get_database_optimization_status,
    optimize_database_indexes,
)
from app.infrastructure.database.migrations import (
    get_database_migration_status,
    run_database_migrations,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("database_optimization.log"),
    ],
)

logger = logging.getLogger(__name__)


def optimize_indexes():
    """
    执行数据库索引优化
    """
    logger.info("开始执行数据库索引优化...")

    try:
        result = optimize_database_indexes()

        print("\n=== 数据库索引优化结果 ===")
        print(f"开始时间: {result['start_time']}")
        print(f"结束时间: {result['end_time']}")
        print(f"总耗时: {result['duration_seconds']:.2f} 秒")
        print(f"完成步骤: {', '.join(result['steps_completed'])}")

        if result.get("index_results"):
            print("\n索引创建结果:")
            for index_name, success in result["index_results"].items():
                status = "✓ 成功" if success else "- 跳过"
                print(f"  {index_name}: {status}")

        if result.get("errors"):
            print("\n错误信息:")
            for error in result["errors"]:
                print(f"  ❌ {error}")

        logger.info("数据库索引优化完成")
        return True

    except Exception as e:
        logger.error(f"数据库索引优化失败: {e}")
        print(f"\n❌ 优化失败: {e}")
        return False


def run_migrations(target_version=None):
    """
    执行数据库迁移

    Args:
        target_version: 目标版本
    """
    logger.info(f"开始执行数据库迁移到版本: {target_version or '最新'}")

    try:
        result = run_database_migrations(target_version)

        print("\n=== 数据库迁移结果 ===")
        print(f"开始时间: {result['start_time']}")
        print(f"结束时间: {result.get('end_time', '未完成')}")
        print(f"总耗时: {result['total_execution_time_ms']} ms")
        print(f"成功: {'是' if result['success'] else '否'}")

        if result["applied_migrations"]:
            print("\n已应用的迁移:")
            for migration in result["applied_migrations"]:
                print(
                    f"  ✓ {migration['version']}: {migration['name']} ({migration['execution_time_ms']}ms)"
                )
        else:
            print("\n没有需要应用的迁移")

        if result.get("errors"):
            print("\n错误信息:")
            for error in result["errors"]:
                print(f"  ❌ {error}")

        logger.info("数据库迁移完成")
        return result["success"]

    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        print(f"\n❌ 迁移失败: {e}")
        return False


def show_status():
    """
    显示数据库优化状态
    """
    logger.info("获取数据库优化状态...")

    try:
        # 获取优化状态
        opt_status = get_database_optimization_status()

        # 获取迁移状态
        migration_status = get_database_migration_status()

        print("\n=== 数据库优化状态 ===")

        # 显示表统计信息
        if (
            "query_analysis" in opt_status
            and "table_stats" in opt_status["query_analysis"]
        ):
            print("\n表统计信息:")
            for table, stats in opt_status["query_analysis"]["table_stats"].items():
                print(
                    f"  {table}: {stats['total_records']:,} 条记录 (~{stats['estimated_size_mb']:.1f} MB)"
                )

        # 显示现有索引
        if (
            "index_usage" in opt_status
            and "existing_indexes" in opt_status["index_usage"]
        ):
            print(
                f"\n现有索引 ({len(opt_status['index_usage']['existing_indexes'])} 个):"
            )
            for index in opt_status["index_usage"]["existing_indexes"]:
                print(f"  • {index['name']} (表: {index['table']})")

        # 显示优化建议
        if "recommendations" in opt_status:
            print("\n优化建议:")
            for i, rec in enumerate(opt_status["recommendations"], 1):
                print(f"  {i}. {rec}")

        # 显示迁移状态
        print("\n=== 数据库迁移状态 ===")

        if "applied_migrations" in migration_status:
            print(f"\n已应用的迁移 ({len(migration_status['applied_migrations'])} 个):")
            for migration in migration_status["applied_migrations"]:
                print(
                    f"  ✓ {migration['version']}: {migration['name']} (应用于: {migration['applied_at']})"
                )

        if "pending_migrations" in migration_status:
            if migration_status["pending_migrations"]:
                print(
                    f"\n待执行的迁移 ({len(migration_status['pending_migrations'])} 个):"
                )
                for migration in migration_status["pending_migrations"]:
                    print(
                        f"  ⏳ {migration['version']}: {migration['name']} - {migration['description']}"
                    )
            else:
                print("\n✓ 所有迁移都已应用")

        logger.info("状态获取完成")
        return True

    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        print(f"\n❌ 获取状态失败: {e}")
        return False


def full_optimization():
    """
    执行完整的数据库优化流程
    """
    logger.info("开始执行完整的数据库优化流程...")

    print("\n🚀 开始完整数据库优化流程")
    print("=" * 50)

    success = True

    # 步骤1: 执行迁移
    print("\n📋 步骤 1/2: 执行数据库迁移")
    if not run_migrations():
        success = False
        print("❌ 迁移失败，停止优化流程")
        return False

    # 步骤2: 优化索引
    print("\n🔧 步骤 2/2: 优化数据库索引")
    if not optimize_indexes():
        success = False
        print("⚠️ 索引优化失败，但迁移已完成")

    if success:
        print("\n🎉 数据库优化流程全部完成！")
        print("\n建议执行以下命令查看优化效果:")
        print("  python optimize_database.py --status")
    else:
        print("\n⚠️ 优化流程部分失败，请检查日志")

    return success


def export_status(output_file):
    """
    导出数据库状态到文件

    Args:
        output_file: 输出文件路径
    """
    logger.info(f"导出数据库状态到文件: {output_file}")

    try:
        # 获取状态信息
        opt_status = get_database_optimization_status()
        migration_status = get_database_migration_status()

        # 合并状态信息
        full_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "optimization_status": opt_status,
            "migration_status": migration_status,
        }

        # 写入文件
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(full_status, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n✓ 状态已导出到: {output_file}")
        logger.info(f"状态导出完成: {output_file}")
        return True

    except Exception as e:
        logger.error(f"状态导出失败: {e}")
        print(f"\n❌ 导出失败: {e}")
        return False


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description="ChronoRetrace 数据库优化管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python optimize_database.py --status                    # 查看当前状态
  python optimize_database.py --optimize                  # 执行完整优化
  python optimize_database.py --indexes                   # 仅优化索引
  python optimize_database.py --migrate                   # 执行迁移
  python optimize_database.py --migrate --version 001     # 迁移到指定版本
  python optimize_database.py --export status.json       # 导出状态到文件
        """,
    )

    parser.add_argument("--status", action="store_true", help="显示数据库优化状态")
    parser.add_argument(
        "--optimize", action="store_true", help="执行完整的数据库优化流程"
    )
    parser.add_argument("--indexes", action="store_true", help="仅执行索引优化")
    parser.add_argument("--migrate", action="store_true", help="执行数据库迁移")
    parser.add_argument("--version", type=str, help="指定迁移目标版本")
    parser.add_argument("--export", type=str, metavar="FILE", help="导出状态到指定文件")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 执行相应操作
    success = True

    if args.status:
        success = show_status()
    elif args.optimize:
        success = full_optimization()
    elif args.indexes:
        success = optimize_indexes()
    elif args.migrate:
        success = run_migrations(args.version)
    elif args.export:
        success = export_status(args.export)
    else:
        parser.print_help()
        return 0

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
