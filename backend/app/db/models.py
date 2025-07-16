from sqlalchemy import Column, String, Float, Date, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from .session import Base
from datetime import datetime

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
    interval = Column(String, nullable=False, default='daily') # Add interval column

    __table_args__ = (UniqueConstraint('ts_code', 'trade_date', 'interval', name='_ts_code_trade_date_interval_uc'),)

class StockInfo(Base):
    __tablename__ = "stock_info"

    ts_code = Column(String, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('ts_code', name='_ts_code_uc'),)

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
    value = Column(Float, nullable=False) # Dividend per share or split coefficient

    __table_args__ = (UniqueConstraint('symbol', 'ex_date', 'action_type', name='_symbol_date_action_uc'),)

class AnnualEarnings(Base):
    __tablename__ = "annual_earnings"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    year = Column(Integer, index=True, nullable=False)
    net_profit = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint('symbol', 'year', name='_symbol_year_uc'),)