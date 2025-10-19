import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.schemas.screener import ScreenerRequest, ScreenerResponse
from app.services.screener_service import screen_stocks

router = APIRouter()


@router.post("/screener/", response_model=ScreenerResponse)
async def screen_stocks_endpoint(
    request: ScreenerRequest,
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
        error_msg = f"Screener error: {e!s}\n{traceback.format_exc()}"
        logging.exception(error_msg)
        # Generic error handler for unexpected issues
        raise HTTPException(
            status_code=500, detail="An internal error occurred."
        ) from e
