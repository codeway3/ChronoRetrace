from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship
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


# 用户认证与管理相关模型
class User(Base):
    """用户核心表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)  # male, female, other
    profession = Column(String(100), nullable=True)
    investment_experience = Column(String(20), default="beginner")  # beginner, intermediate, advanced, expert

    # 账户状态
    is_active = Column(Boolean, default=True, index=True)
    is_locked = Column(Boolean, default=False, index=True)
    vip_level = Column(Integer, default=0, index=True)  # 0: normal, 1: vip, 2: premium
    email_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)

    # 安全相关
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    email_verification_token = Column(String(255), nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # 关系
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    watchlists = relationship("UserWatchlist", back_populates="user")
    portfolios = relationship("UserPortfolio", back_populates="user")
    role_assignments = relationship("UserRoleAssignment", back_populates="user", foreign_keys="UserRoleAssignment.user_id")
    sessions = relationship("UserSession", back_populates="user")
    activity_logs = relationship("UserActivityLog", back_populates="user")

    __table_args__ = (
        Index("idx_users_email_verified", "email_verified"),
        Index("idx_users_created_at", "created_at"),
    )


class UserRole(Base):
    """用户角色表"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # super_admin, admin, vip_user, normal_user, guest
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)  # JSON格式存储权限列表
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    assignments = relationship("UserRoleAssignment", back_populates="role")


class UserRoleAssignment(Base):
    """用户角色分配表"""
    __tablename__ = "user_role_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("user_roles.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 关系
    user = relationship("User", back_populates="role_assignments", foreign_keys=[user_id])
    role = relationship("UserRole", back_populates="assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="_user_role_uc"),
    )


class UserPreferences(Base):
    """用户偏好设置表"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # 界面偏好
    theme_mode = Column(String(20), default="light")  # light, dark, auto
    language = Column(String(10), default="zh-CN")
    timezone = Column(String(50), default="Asia/Shanghai")
    currency = Column(String(10), default="CNY")

    # 通知设置
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)

    # 数据展示偏好
    default_chart_type = Column(String(20), default="candlestick")
    default_period = Column(String(10), default="daily")
    preferred_indicators = Column(Text, nullable=True)  # JSON格式存储技术指标偏好

    # 投资偏好
    risk_tolerance = Column(String(20), default="moderate")  # conservative, moderate, aggressive
    investment_goal = Column(String(50), nullable=True)
    investment_horizon = Column(String(20), nullable=True)  # short_term, medium_term, long_term

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="preferences")


class UserWatchlist(Base):
    """用户自选股分组表"""
    __tablename__ = "user_watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="watchlists")
    items = relationship("UserWatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="_user_watchlist_name_uc"),
    )


class UserWatchlistItem(Base):
    """用户自选股项目表"""
    __tablename__ = "user_watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("user_watchlists.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market = Column(String(20), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    target_price = Column(Numeric(10, 2), nullable=True)
    stop_loss_price = Column(Numeric(10, 2), nullable=True)
    sort_order = Column(Integer, default=0)

    # 提醒设置
    price_alert_enabled = Column(Boolean, default=False)
    price_alert_threshold = Column(Numeric(5, 2), nullable=True)  # 涨跌幅百分比
    volume_alert_enabled = Column(Boolean, default=False)

    # 关系
    watchlist = relationship("UserWatchlist", back_populates="items")

    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", "market", name="_watchlist_symbol_market_uc"),
    )


class UserPortfolio(Base):
    """用户投资组合表"""
    __tablename__ = "user_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    initial_capital = Column(Numeric(15, 2), nullable=True)
    current_value = Column(Numeric(15, 2), nullable=True)
    total_return = Column(Numeric(15, 2), nullable=True)
    total_return_pct = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("UserPortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("UserTransaction", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="_user_portfolio_name_uc"),
    )


class UserPortfolioHolding(Base):
    """用户投资组合持仓表"""
    __tablename__ = "user_portfolio_holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    average_cost = Column(Numeric(10, 2), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=True)
    market_value = Column(Numeric(15, 2), nullable=True)
    unrealized_pnl = Column(Numeric(15, 2), nullable=True)
    unrealized_pnl_pct = Column(Numeric(5, 2), nullable=True)
    first_purchase_date = Column(Date, nullable=True)
    last_update_date = Column(Date, nullable=True)

    # 关系
    portfolio = relationship("UserPortfolio", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", "market", name="_portfolio_symbol_market_uc"),
    )


class UserTransaction(Base):
    """用户交易记录表"""
    __tablename__ = "user_transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market = Column(String(20), nullable=False)
    transaction_type = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    commission = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)
    transaction_date = Column(DateTime, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    portfolio = relationship("UserPortfolio", back_populates="transactions")

    __table_args__ = (
        Index("idx_transactions_symbol_date", "symbol", "transaction_date"),
        Index("idx_transactions_type_date", "transaction_type", "transaction_date"),
    )


class UserSession(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True)
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_user_active", "user_id", "is_active"),
        Index("idx_sessions_expires", "expires_at"),
    )


class UserActivityLog(Base):
    """用户行为日志表"""
    __tablename__ = "user_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(200), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    user = relationship("User", back_populates="activity_logs")

    __table_args__ = (
        Index("idx_user_activity_logs_user", "user_id"),
        Index("idx_user_activity_logs_action", "action"),
        Index("idx_user_activity_logs_created", "created_at"),
        Index("idx_user_activity_logs_success", "success"),
    )
