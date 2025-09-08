import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.backtest import backtester
from app.infrastructure.database.session import get_db
from app.schemas.backtest import (
    BacktestOptimizationResponse,
    BacktestResult,
    GridStrategyConfig,
    GridStrategyOptimizeConfig,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/grid", response_model=BacktestResult)
def run_grid_backtest_api(config: GridStrategyConfig, db: Session = Depends(get_db)):
    """
    API endpoint to run a single grid trading backtest.
    """
    try:
        if config.start_date > config.end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before or equal to end date.",
            )
        logger.info(f"Received single grid backtest request for {config.stock_code}")
        result = backtester.run_grid_backtest(db=db, config=config)
        return result
    except ValueError as e:
        logger.error(
            f"ValueError during backtest for {config.stock_code}: {e}", exc_info=True
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during backtest for {config.stock_code}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="An internal error occurred during the backtest."
        ) from e


@router.post("/grid/optimize", response_model=BacktestOptimizationResponse)
def run_grid_optimization_api(
    config: GridStrategyOptimizeConfig, db: Session = Depends(get_db)
):
    """
    API endpoint to run a grid trading parameter optimization.
    """
    try:
        if config.start_date > config.end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before or equal to end date.",
            )
        logger.info(f"Received grid optimization request for {config.stock_code}")
        result = backtester.run_grid_optimization(db=db, config=config)
        return result
    except ValueError as e:
        logger.error(
            f"ValueError during optimization for {config.stock_code}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during optimization for {config.stock_code}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="An internal error occurred during optimization."
        ) from e
