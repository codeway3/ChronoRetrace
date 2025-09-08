from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.screener.screener_service import screen_stocks
from app.infrastructure.database.session import get_db
from app.schemas.stock import StockScreenerRequest, StockScreenerResponse

router = APIRouter()


@router.post("/screener/stocks", response_model=StockScreenerResponse)
async def screen_stocks_endpoint(
    request: StockScreenerRequest,
    db: Session = Depends(get_db),
):
    """
    Screens stocks based on a dynamic set of filtering conditions.

    This endpoint allows you to find stocks that match specific fundamental
    and technical criteria.
    """
    try:
        return screen_stocks(db=db, request=request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # 记录异常详情以便调试
        import logging
        import traceback

        error_msg = f"Screener error: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        # Generic error handler for unexpected issues
        raise HTTPException(status_code=500, detail="An internal error occurred.") from e
