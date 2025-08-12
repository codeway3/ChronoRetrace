
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime, timedelta

from starlette.concurrency import run_in_threadpool

from app.schemas.stock import StockDataBase
from app.services import commodity_fetcher
from fastapi_cache.decorator import cache

router = APIRouter()
logger = logging.getLogger(__name__)

# A list of known commodity symbols for suggestion/validation
KNOWN_COMMODITY_SYMBOLS = {
    "GC=F": "黄金",
    "SI=F": "白银",
    "CL=F": "原油",
    "NG=F": "天然气",
    "HG=F": "铜",
    "ZC=F": "玉米",
    "ZS=F": "大豆",
    "KC=F": "咖啡",
    "CT=F": "棉花",
    "SB=F": "糖",
}

@router.get("/list", response_model=dict[str, str])
@cache(expire=86400)  # Cache for 24 hours
async def get_commodity_list():
    """
    Get a list of known commodity symbols.
    """
    return KNOWN_COMMODITY_SYMBOLS


@router.get("/{symbol}", response_model=List[StockDataBase])
@cache(expire=900)  # Cache for 15 minutes
async def get_commodity_data(
    symbol: str,
    interval: str = Query("daily", enum=["daily", "weekly", "monthly"]),
):
    """
    Get historical data for a specific commodity using yfinance.
    """
    start_date = (datetime.now() - timedelta(days=10 * 365)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        df = await run_in_threadpool(
            commodity_fetcher.fetch_commodity_from_yfinance,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )

        if df.empty:
            return []

        dict_records = df.to_dict("records")
        for record in dict_records:
            record["ts_code"] = symbol
            record["interval"] = interval
            
        records = [StockDataBase.model_validate(record) for record in dict_records]

        return records

    except Exception as e:
        logger.error(f"Failed to fetch commodity data for {symbol}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {symbol}: {str(e)}")
