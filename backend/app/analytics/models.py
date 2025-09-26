"""
策略数据库模型
"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Strategy(Base):
    """策略模型"""

    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    definition = Column(JSON, nullable=False)  # 策略逻辑定义
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class BacktestResult(Base):
    """回测结果模型"""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(
        Integer, ForeignKey("strategies.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 回测参数
    symbol = Column(String(50), nullable=False)
    interval = Column(String(10), nullable=False)  # 1d, 1h, etc.
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Integer, nullable=False, default=100000)

    # 性能指标
    total_return = Column(Integer)  # 总收益率百分比
    annual_return = Column(Integer)
    sharpe_ratio = Column(Integer)  # 夏普比率 * 100
    max_drawdown = Column(Integer)  # 最大回撤百分比
    win_rate = Column(Integer)  # 胜率百分比

    # 交易统计
    total_trades = Column(Integer)
    profitable_trades = Column(Integer)

    # 原始数据
    equity_curve = Column(JSON)  # 权益曲线数据
    trades = Column(JSON)  # 交易记录

    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<BacktestResult(id={self.id}, strategy_id={self.strategy_id}, return={self.total_return}%)>"
