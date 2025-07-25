from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.backtest import GridStrategyConfig, BacktestResult
from app.services import backtester
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/grid", response_model=BacktestResult)
def run_grid_backtest_api(
    config: GridStrategyConfig, 
    db: Session = Depends(get_db)
):
    """
    API endpoint to run a grid trading backtest.
    Receives strategy configuration and returns detailed backtest results.
    """
    try:
        logger.info(f"Received grid backtest request for {config.stock_code}")
        result = backtester.run_grid_backtest(db=db, config=config)
        return result
    except ValueError as e:
        logger.error(f"ValueError during backtest for {config.stock_code}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred during backtest for {config.stock_code}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during the backtest.")
