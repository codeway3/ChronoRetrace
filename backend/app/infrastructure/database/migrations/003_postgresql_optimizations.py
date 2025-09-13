"""PostgreSQL数据库优化和扩展

迁移版本: 003
创建时间: 2024-01-15
描述: 添加PostgreSQL特定的扩展、索引优化和性能配置
"""

from sqlalchemy import text


def upgrade(engine):
    """执行数据库升级"""
    with engine.connect() as conn:
        # 启用UUID扩展
        try:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            print("✅ UUID扩展已启用")
        except Exception as e:
            print(f"⚠️ UUID扩展启用失败: {e}")

        # 启用pg_trgm扩展用于文本搜索
        try:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
            print("✅ pg_trgm扩展已启用")
        except Exception as e:
            print(f"⚠️ pg_trgm扩展启用失败: {e}")

        # 启用btree_gin扩展用于复合索引
        try:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "btree_gin"'))
            print("✅ btree_gin扩展已启用")
        except Exception as e:
            print(f"⚠️ btree_gin扩展启用失败: {e}")

        # 为股票数据表创建分区索引
        try:
            conn.execute(
                text(
                    """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_data_ts_code_date_partial
                ON stock_data (ts_code, trade_date)
                WHERE trade_date >= CURRENT_DATE - INTERVAL '1 year'
            """
                )
            )
            print("✅ 股票数据分区索引已创建")
        except Exception as e:
            print(f"⚠️ 股票数据分区索引创建失败: {e}")

        # 为用户表创建文本搜索索引
        try:
            conn.execute(
                text(
                    """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_fulltext_search
                ON users USING gin(to_tsvector('english', coalesce(username, '') || ' ' || coalesce(full_name, '') || ' ' || coalesce(email, '')))
            """
                )
            )
            print("✅ 用户全文搜索索引已创建")
        except Exception as e:
            print(f"⚠️ 用户全文搜索索引创建失败: {e}")

        # 创建数据质量监控视图
        try:
            conn.execute(
                text(
                    """
                CREATE OR REPLACE VIEW data_quality_summary AS
                SELECT 
                    table_name,
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN validation_status = 'validated' THEN 1 END) as validated_records,
                    COUNT(CASE WHEN is_duplicate = true THEN 1 END) as duplicate_records,
                    AVG(quality_score) as avg_quality_score,
                    MAX(updated_at) as last_update
                FROM data_quality_logs
                GROUP BY table_name
            """
                )
            )
            print("✅ 数据质量监控视图已创建")
        except Exception as e:
            print(f"⚠️ 数据质量监控视图创建失败: {e}")

        # 设置数据库连接参数优化
        try:
            conn.execute(text("SET shared_preload_libraries = 'pg_stat_statements'"))
            conn.execute(text("SET log_statement = 'all'"))
            conn.execute(text("SET log_min_duration_statement = 1000"))
            print("✅ 数据库性能参数已优化")
        except Exception as e:
            print(f"⚠️ 数据库性能参数优化失败: {e}")

        conn.commit()

    print("✅ PostgreSQL优化和扩展配置完成")


def downgrade(engine):
    """执行数据库降级"""
    with engine.connect() as conn:
        # 删除创建的索引
        try:
            conn.execute(
                text(
                    "DROP INDEX CONCURRENTLY IF EXISTS idx_stock_data_ts_code_date_partial"
                )
            )
            conn.execute(
                text("DROP INDEX CONCURRENTLY IF EXISTS idx_users_fulltext_search")
            )
            print("✅ 自定义索引已删除")
        except Exception as e:
            print(f"⚠️ 索引删除失败: {e}")

        # 删除视图
        try:
            conn.execute(text("DROP VIEW IF EXISTS data_quality_summary"))
            print("✅ 数据质量监控视图已删除")
        except Exception as e:
            print(f"⚠️ 视图删除失败: {e}")

        # 注意：不删除扩展，因为可能被其他应用使用

        conn.commit()

    print("⚠️ PostgreSQL优化配置已回滚")
