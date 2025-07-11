from sqlalchemy import Column, String, Float, Date, Integer, DateTime
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
