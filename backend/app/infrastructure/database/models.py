from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.schema import UniqueConstraint

from .session import Base


class StockData(Base):
    __tablename__ = "stock_data"

    id = Column(Integer, primary_key=True, index=True)
    ts_code = Column(String, index=True, nullable=False)
    trade_date = Column(Date, index=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    pre_close = Column(Float)
    change = Column(Float)
    pct_chg = Column(Float)
    vol = Column(Float)
    amount = Column(Float)
    interval = Column(String, index=True, nullable=False, default="daily")

    __table_args__ = (
        UniqueConstraint(
            "ts_code", "trade_date", "interval", name="_ts_code_trade_date_interval_uc"
        ),
        # 性能优化索引
        Index(
            "idx_stock_data_ts_code_date_interval", "ts_code", "trade_date", "interval"
        ),
    )


class StockInfo(Base):
    __tablename__ = "stock_info"

    ts_code = Column(String, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    market_type = Column(String, nullable=False, default="A_share")  # New column
    last_updated = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ts_code", "market_type", name="_ts_code_market_type_uc"),
    )


class FundamentalData(Base):
    __tablename__ = "fundamental_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, unique=True, nullable=False)
    market_cap = Column(Float)
    pe_ratio = Column(Float)
    dividend_yield = Column(Float)
    eps = Column(Float)
    beta = Column(Float)
    gross_profit_margin = Column(Float)
    net_profit_margin = Column(Float)
    roe = Column(Float)
    revenue_growth_rate = Column(Float)
    net_profit_growth_rate = Column(Float)
    debt_to_asset_ratio = Column(Float)
    current_ratio = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    action_type = Column(String, nullable=False)  # 'dividend' or 'split'
    ex_date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)  # Dividend per share or split coefficient

    __table_args__ = (
        UniqueConstraint(
            "symbol", "ex_date", "action_type", name="_symbol_date_action_uc"
        ),
    )


class AnnualEarnings(Base):
    __tablename__ = "annual_earnings"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    year = Column(Integer, index=True, nullable=False)
    net_profit = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("symbol", "year", name="_symbol_year_uc"),)


class DailyStockMetrics(Base):
    __tablename__ = "daily_stock_metrics"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    market = Column(String, index=True, nullable=False)
    close_price = Column(Float)
    pe_ratio = Column(Float, index=True)
    pb_ratio = Column(Float, index=True)
    market_cap = Column(Integer, index=True)
    dividend_yield = Column(Float, index=True)
    ma5 = Column(Float)
    ma20 = Column(Float)
    volume = Column(Integer)
    # 数据质量追踪字段
    data_source = Column(String, index=True, nullable=True)  # 数据来源
    quality_score = Column(Float, default=0.0)  # 数据质量评分 (0-1)
    validation_status = Column(String, default="pending")  # pending, validated, failed
    last_validated = Column(DateTime, nullable=True)  # 最后验证时间
    is_duplicate = Column(Boolean, default=False, index=True)  # 是否为重复数据
    duplicate_source = Column(String, nullable=True)  # 重复数据来源标识
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("code", "date", "market", name="_code_date_market_uc"),
        # 性能优化索引
        Index("idx_daily_metrics_code_date", "code", "date"),
        Index("idx_daily_metrics_market_date", "market", "date"),
        Index("idx_daily_metrics_updated_at", "updated_at"),
        # 部分索引用于筛选查询
        Index(
            "idx_daily_metrics_pe_ratio_range",
            "pe_ratio",
            postgresql_where=text("pe_ratio IS NOT NULL AND pe_ratio > 0"),
        ),
        Index(
            "idx_daily_metrics_market_cap_range",
            "market_cap",
            postgresql_where=text("market_cap IS NOT NULL AND market_cap > 0"),
        ),
    )


class DataQualityLog(Base):
    """数据质量日志表，记录校验和去重过程"""

    __tablename__ = "data_quality_logs"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, index=True, nullable=False)  # 关联的数据记录ID
    table_name = Column(String, index=True, nullable=False)  # 数据表名
    operation_type = Column(
        String, index=True, nullable=False
    )  # validation, deduplication
    status = Column(String, nullable=False)  # success, failed, warning
    message = Column(Text, nullable=True)  # 详细信息
    error_details = Column(Text, nullable=True)  # 错误详情
    execution_time = Column(Float, nullable=True)  # 执行时间(秒)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "table_name",
            "operation_type",
            "created_at",
            name="_record_table_operation_time_uc",
        ),
    )
