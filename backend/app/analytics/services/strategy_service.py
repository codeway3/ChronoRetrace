"""
策略服务层 - 策略管理和存储逻辑
"""

from typing import Any

from sqlalchemy.orm import Session

from app.analytics.backtest.backtester import run_grid_backtest, run_grid_optimization
from app.analytics.models import BacktestResult, Strategy
from app.schemas.asset_types import AssetType
from app.schemas.backtest import GridStrategyConfig, GridStrategyOptimizeConfig


class StrategyService:
    """策略服务类"""

    def __init__(self, db: Session):
        self.db = db

    def create_strategy(
        self,
        user_id: int,
        name: str,
        definition: dict[str, Any],
        description: str | None = None,
    ) -> Strategy:
        """创建新策略"""
        strategy = Strategy(
            user_id=user_id, name=name, description=description, definition=definition
        )
        self.db.add(strategy)
        self.db.commit()
        self.db.refresh(strategy)
        return strategy

    def get_user_strategies(self, user_id: int) -> list[Strategy]:
        """获取用户的所有策略"""
        return self.db.query(Strategy).filter(Strategy.user_id == user_id).all()

    def get_strategy_by_id(self, strategy_id: int, user_id: int) -> Strategy | None:
        """根据ID获取策略"""
        return (
            self.db.query(Strategy)
            .filter(Strategy.id == strategy_id, Strategy.user_id == user_id)
            .first()
        )

    def update_strategy(
        self, strategy_id: int, user_id: int, **kwargs
    ) -> Strategy | None:
        """更新策略"""
        strategy = self.get_strategy_by_id(strategy_id, user_id)
        if not strategy:
            return None

        for key, value in kwargs.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)

        self.db.commit()
        self.db.refresh(strategy)
        return strategy

    def delete_strategy(self, strategy_id: int, user_id: int) -> bool:
        """删除策略"""
        strategy = self.get_strategy_by_id(strategy_id, user_id)
        if not strategy:
            return False

        self.db.delete(strategy)
        self.db.commit()
        return True


class BacktestService:
    """回测服务类"""

    def __init__(self, db: Session):
        self.db = db

    def save_backtest_result(
        self,
        strategy_id: int,
        user_id: int,
        symbol: str,
        interval: str,
        start_date,
        end_date,
        initial_capital: int,
        performance_metrics: dict[str, Any],
        equity_curve: list[dict],
        trades: list[dict],
    ) -> BacktestResult:
        """保存回测结果"""
        result = BacktestResult(
            strategy_id=strategy_id,
            user_id=user_id,
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            total_return=performance_metrics.get("total_return"),
            annual_return=performance_metrics.get("annual_return"),
            sharpe_ratio=performance_metrics.get("sharpe_ratio"),
            max_drawdown=performance_metrics.get("max_drawdown"),
            win_rate=performance_metrics.get("win_rate"),
            total_trades=performance_metrics.get("total_trades"),
            profitable_trades=performance_metrics.get("profitable_trades"),
            equity_curve=equity_curve,
            trades=trades,
        )

        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_backtest_results(
        self, user_id: int, strategy_id: int | None = None
    ) -> list[BacktestResult]:
        """获取回测结果"""
        query = self.db.query(BacktestResult).filter(BacktestResult.user_id == user_id)
        if strategy_id:
            query = query.filter(BacktestResult.strategy_id == strategy_id)
        return query.order_by(BacktestResult.created_at.desc()).all()

    def get_backtest_result_by_id(
        self, result_id: int, user_id: int
    ) -> BacktestResult | None:
        """根据ID获取回测结果"""
        return (
            self.db.query(BacktestResult)
            .filter(BacktestResult.id == result_id, BacktestResult.user_id == user_id)
            .first()
        )

    async def backtest_by_asset_type(
        self, asset_type: AssetType, config: GridStrategyConfig, db: Session
    ):
        """按资产类型执行回溯测试"""
        if asset_type == AssetType.CRYPTO or asset_type == AssetType.US_STOCK:
            return run_grid_backtest(db, config)
        else:
            raise ValueError(f"不支持的资产类型: {asset_type}")

    async def optimize_by_asset_type(
        self, asset_type: AssetType, config: GridStrategyOptimizeConfig, db: Session
    ):
        """按资产类型优化策略参数"""
        if asset_type == AssetType.CRYPTO or asset_type == AssetType.US_STOCK:
            return run_grid_optimization(db, config)
        else:
            raise ValueError(f"不支持的资产类型: {asset_type}")

    def get_supported_strategies(self, asset_type: AssetType) -> list[str]:
        """获取指定资产类型支持的策略列表"""
        if asset_type == AssetType.CRYPTO or asset_type == AssetType.US_STOCK:
            return ["grid_strategy"]
        else:
            return []
