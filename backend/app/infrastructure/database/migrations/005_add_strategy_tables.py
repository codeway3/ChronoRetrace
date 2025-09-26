"""添加策略相关数据表

迁移版本: 005
创建时间: 2024-01-25
描述: 创建策略管理和回测结果相关表
"""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.sql import func


def upgrade(engine):
    """执行数据库升级"""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 检查users表是否存在
    if "users" not in existing_tables:
        print("❌ users表不存在，无法创建策略表")
        raise Exception("users表不存在，请先执行用户认证相关迁移")

    try:
        # 创建strategies表
        if "strategies" not in existing_tables:
            print("正在创建strategies表...")

            # 定义strategies表结构（先创建表，后添加外键）
            strategies_table = Table(
                "strategies",
                MetaData(),
                Column("id", Integer, primary_key=True, index=True),
                Column("user_id", Integer, nullable=False, index=True),
                Column("name", String(255), nullable=False),
                Column("description", Text),
                Column("definition", JSON, nullable=False),
                Column("created_at", DateTime, server_default=func.now()),
                Column(
                    "updated_at",
                    DateTime,
                    server_default=func.now(),
                    onupdate=func.now(),
                ),
            )
            strategies_table.create(engine)

            # 添加外键约束
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE strategies ADD CONSTRAINT fk_strategies_user_id FOREIGN KEY (user_id) REFERENCES users(id)"
                    )
                )
            print("✅ strategies表创建完成")
        else:
            print("✅ strategies表已存在")

        # 创建backtest_results表
        if "backtest_results" not in existing_tables:
            print("正在创建backtest_results表...")

            # 定义backtest_results表结构（先创建表，后添加外键）
            backtest_results_table = Table(
                "backtest_results",
                MetaData(),
                Column("id", Integer, primary_key=True, index=True),
                Column("strategy_id", Integer, nullable=False, index=True),
                Column("user_id", Integer, nullable=False, index=True),
                Column("symbol", String(50), nullable=False),
                Column("interval", String(10), nullable=False),
                Column("start_date", DateTime, nullable=False),
                Column("end_date", DateTime, nullable=False),
                Column("initial_capital", Integer, nullable=False, default=100000),
                Column("total_return", Integer),
                Column("annual_return", Integer),
                Column("sharpe_ratio", Integer),
                Column("max_drawdown", Integer),
                Column("win_rate", Integer),
                Column("total_trades", Integer),
                Column("profitable_trades", Integer),
                Column("equity_curve", JSON),
                Column("trades", JSON),
                Column("created_at", DateTime, server_default=func.now()),
            )
            backtest_results_table.create(engine)

            # 添加外键约束
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE backtest_results ADD CONSTRAINT fk_backtest_results_strategy_id FOREIGN KEY (strategy_id) REFERENCES strategies(id)"
                    )
                )
                conn.execute(
                    text(
                        "ALTER TABLE backtest_results ADD CONSTRAINT fk_backtest_results_user_id FOREIGN KEY (user_id) REFERENCES users(id)"
                    )
                )
            print("✅ backtest_results表创建完成")
        else:
            print("✅ backtest_results表已存在")

        print("✅ 策略相关数据表创建完成")
        return True

    except Exception as e:
        print(f"❌ 策略相关数据表创建失败: {e}")
        raise


def downgrade(engine):
    """执行数据库降级"""
    try:
        # 删除表
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS backtest_results"))
            conn.execute(text("DROP TABLE IF EXISTS strategies"))

        print("✅ 策略相关数据表删除完成")
        return True

    except Exception as e:
        print(f"❌ 策略相关数据表删除失败: {e}")
        raise


def insert_initial_data(engine):
    """插入初始数据"""
    try:
        with engine.connect() as conn:
            # 检查是否已有数据
            result = conn.execute(text("SELECT COUNT(*) FROM strategies"))
            existing_strategies = result.scalar()

            if existing_strategies == 0:
                print("正在插入示例策略数据...")

                # 插入示例策略数据（使用原始SQL）
                strategy_data = {
                    "user_id": 1,
                    "name": "双均线策略",
                    "description": "简单的移动平均线交叉策略",
                    "definition": {
                        "version": "1.0",
                        "description": "双均线交叉策略",
                        "symbols": ["AAPL", "MSFT"],
                        "interval": "1d",
                        "initial_capital": 100000,
                        "conditions": [
                            {
                                "type": "technical",
                                "indicator": "sma",
                                "operator": ">",
                                "value": 50,
                                "lookback_period": 20,
                            },
                            {
                                "type": "technical",
                                "indicator": "sma",
                                "operator": "<",
                                "value": 20,
                                "lookback_period": 10,
                            },
                        ],
                        "actions": [
                            {
                                "type": "buy",
                                "condition_id": 0,
                                "position_size": 0.5,
                                "stop_loss": 0.05,
                                "take_profit": 0.1,
                            },
                            {"type": "sell", "condition_id": 1, "position_size": 1.0},
                        ],
                        "max_position_size": 0.2,
                        "max_drawdown": 0.15,
                    },
                }

                # 插入策略数据
                conn.execute(
                    text(
                        """
                    INSERT INTO strategies (user_id, name, description, definition, created_at, updated_at)
                    VALUES (:user_id, :name, :description, :definition, NOW(), NOW())
                    """
                    ),
                    strategy_data,
                )

                print("✅ 示例策略数据插入完成")
            else:
                print("✅ 策略数据已存在，跳过初始数据插入")

    except Exception as e:
        print(f"⚠️ 初始数据插入失败: {e}")
