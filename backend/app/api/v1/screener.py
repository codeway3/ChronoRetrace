from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.stock import StockScreenerRequest, StockScreenerResponse
from app.services import screener_service

router = APIRouter()


@router.post("/screener/stocks", response_model=StockScreenerResponse)
async def screen_stocks_endpoint(
    request: StockScreenerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Screens stocks based on a dynamic set of filtering conditions.

    This endpoint allows you to find stocks that match specific fundamental
    and technical criteria.
    """
    try:
        return screener_service.screen_stocks(db=db, request=request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 记录异常详情以便调试
        import logging
        import traceback
        error_msg = f"Screener error: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        # Generic error handler for unexpected issues
        raise HTTPException(
            status_code=500, detail="An internal error occurred.")
