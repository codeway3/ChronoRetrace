"""创建关注列表相关数据表

迁移版本: 002
创建时间: 2024-01-16
描述: 创建股票关注列表、分组等相关表
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func


class MigrationPreconditionError(Exception):
    """迁移前置条件不满足错误"""


Base = declarative_base()


def upgrade(engine):
    """执行数据库升级"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 检查users表是否存在
    if "users" not in existing_tables:
        print("❌ users表不存在，无法创建关注列表表")
        raise MigrationPreconditionError("users表不存在，请先执行001迁移")

    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 关注列表相关数据表创建完成")
    except Exception as e:
        print(f"❌ 关注列表相关数据表创建失败: {e}")
        raise


def downgrade(engine):
    """执行数据库降级"""
    # 删除所有表（谨慎操作）
    Base.metadata.drop_all(bind=engine)
    print("⚠️ 关注列表相关数据表已删除")


# 关注列表分组表
class WatchlistGroup(Base):
    __tablename__ = "watchlist_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # 暂时移除外键约束
    name = Column(String(100), nullable=False)
    description = Column(Text)
    color = Column(String(7), default="#1976d2")  # 十六进制颜色代码
    sort_order = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_watchlist_groups_user", "user_id"),
        Index("idx_watchlist_groups_sort", "sort_order"),
        UniqueConstraint("user_id", "name", name="uq_user_group_name"),
    )


# 关注列表项目表
class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # 暂时移除外键约束
    group_id = Column(Integer, nullable=True)  # 暂时移除外键约束
    symbol = Column(String(20), nullable=False, index=True)  # 股票代码
    market = Column(String(10), nullable=False)  # 市场代码：SH, SZ, HK, US等
    name = Column(String(100))  # 股票名称
    sort_order = Column(Integer, default=0)
    notes = Column(Text)  # 用户备注
    alert_enabled = Column(Boolean, default=False)
    alert_price_high = Column(Numeric(10, 2))  # 价格上限提醒
    alert_price_low = Column(Numeric(10, 2))  # 价格下限提醒
    alert_change_percent = Column(Numeric(5, 2))  # 涨跌幅提醒
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_watchlist_items_user", "user_id"),
        Index("idx_watchlist_items_group", "group_id"),
        Index("idx_watchlist_items_symbol", "symbol"),
        Index("idx_watchlist_items_market", "market"),
        Index("idx_watchlist_items_sort", "sort_order"),
        UniqueConstraint("user_id", "symbol", "market", name="uq_user_symbol_market"),
    )


# 价格提醒历史表
class PriceAlertHistory(Base):
    __tablename__ = "price_alert_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # 暂时移除外键约束
    watchlist_item_id = Column(Integer, nullable=False)  # 暂时移除外键约束
    alert_type = Column(
        String(20), nullable=False
    )  # price_high, price_low, change_percent
    trigger_value = Column(Numeric(10, 2), nullable=False)
    actual_value = Column(Numeric(10, 2), nullable=False)
    message = Column(Text)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_price_alert_history_user", "user_id"),
        Index("idx_price_alert_history_item", "watchlist_item_id"),
        Index("idx_price_alert_history_type", "alert_type"),
        Index("idx_price_alert_history_sent", "is_sent"),
        Index("idx_price_alert_history_created", "created_at"),
    )


# 股票数据缓存表
class StockDataCache(Base):
    __tablename__ = "stock_data_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market = Column(String(10), nullable=False)
    name = Column(String(100))
    current_price = Column(Numeric(10, 2))
    change_amount = Column(Numeric(10, 2))
    change_percent = Column(Numeric(5, 2))
    volume = Column(Integer)
    turnover = Column(Numeric(15, 2))
    high = Column(Numeric(10, 2))
    low = Column(Numeric(10, 2))
    open_price = Column(Numeric(10, 2))
    prev_close = Column(Numeric(10, 2))
    market_cap = Column(Numeric(20, 2))
    pe_ratio = Column(Numeric(8, 2))
    pb_ratio = Column(Numeric(8, 2))
    data_source = Column(String(50))  # 数据来源
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_stock_data_cache_symbol", "symbol"),
        Index("idx_stock_data_cache_market", "market"),
        Index("idx_stock_data_cache_updated", "last_updated"),
        UniqueConstraint("symbol", "market", name="uq_symbol_market"),
    )
