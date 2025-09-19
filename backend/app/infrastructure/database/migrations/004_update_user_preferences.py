"""更新用户偏好设置表结构

迁移版本: 004
创建时间: 2024-01-20
描述: 为user_preferences表添加缺失的字段，使其与模型定义保持一致
"""

from sqlalchemy import text


def upgrade(engine):
    """执行数据库升级"""
    with engine.connect() as conn:
        # 添加currency字段
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'CNY'
            """
                )
            )
            print("✅ currency字段已添加")
        except Exception as e:
            print(f"⚠️ currency字段添加失败: {e}")

        # 重命名notification字段以匹配模型
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                RENAME COLUMN notification_email TO email_notifications
            """
                )
            )
            print("✅ notification_email字段已重命名为email_notifications")
        except Exception as e:
            print(f"⚠️ notification_email字段重命名失败: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                RENAME COLUMN notification_sms TO sms_notifications
            """
                )
            )
            print("✅ notification_sms字段已重命名为sms_notifications")
        except Exception as e:
            print(f"⚠️ notification_sms字段重命名失败: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                RENAME COLUMN notification_push TO push_notifications
            """
                )
            )
            print("✅ notification_push字段已重命名为push_notifications")
        except Exception as e:
            print(f"⚠️ notification_push字段重命名失败: {e}")

        # 添加数据展示偏好字段
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS default_chart_type VARCHAR(20) DEFAULT 'candlestick'
            """
                )
            )
            print("✅ default_chart_type字段已添加")
        except Exception as e:
            print(f"⚠️ default_chart_type字段添加失败: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS default_period VARCHAR(10) DEFAULT 'daily'
            """
                )
            )
            print("✅ default_period字段已添加")
        except Exception as e:
            print(f"⚠️ default_period字段添加失败: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS preferred_indicators TEXT
            """
                )
            )
            print("✅ preferred_indicators字段已添加")
        except Exception as e:
            print(f"⚠️ preferred_indicators字段添加失败: {e}")

        # 添加投资偏好字段
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS risk_tolerance VARCHAR(20) DEFAULT 'moderate'
            """
                )
            )
            print("✅ risk_tolerance字段已添加")
        except Exception as e:
            print(f"⚠️ risk_tolerance字段添加失败: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS investment_goal VARCHAR(50)
            """
                )
            )
            print("✅ investment_goal字段已添加")
        except Exception as e:
            print(f"⚠️ investment_goal字段添加失败: {e}")

        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS investment_horizon VARCHAR(20)
            """
                )
            )
            print("✅ investment_horizon字段已添加")
        except Exception as e:
            print(f"⚠️ investment_horizon字段添加失败: {e}")

        conn.commit()

    print("✅ user_preferences表结构更新完成")


def downgrade(engine):
    """执行数据库降级"""
    with engine.connect() as conn:
        # 删除新添加的字段
        try:
            conn.execute(
                text("ALTER TABLE user_preferences DROP COLUMN IF EXISTS currency")
            )
            conn.execute(
                text(
                    "ALTER TABLE user_preferences DROP COLUMN IF EXISTS default_chart_type"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE user_preferences DROP COLUMN IF EXISTS default_period"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE user_preferences DROP COLUMN IF EXISTS preferred_indicators"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE user_preferences DROP COLUMN IF EXISTS risk_tolerance"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE user_preferences DROP COLUMN IF EXISTS investment_goal"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE user_preferences DROP COLUMN IF EXISTS investment_horizon"
                )
            )
            print("✅ 新添加的字段已删除")
        except Exception as e:
            print(f"⚠️ 删除新字段失败: {e}")

        # 恢复原字段名
        try:
            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                RENAME COLUMN email_notifications TO notification_email
            """
                )
            )

            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                RENAME COLUMN sms_notifications TO notification_sms
            """
                )
            )

            conn.execute(
                text(
                    """
                ALTER TABLE user_preferences
                RENAME COLUMN push_notifications TO notification_push
            """
                )
            )
            print("✅ 字段名已恢复")
        except Exception as e:
            print(f"⚠️ 恢复字段名失败: {e}")

        conn.commit()

    print("⚠️ user_preferences表结构已回滚")
