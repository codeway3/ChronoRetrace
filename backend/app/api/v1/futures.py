import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime, timedelta
import akshare as ak
from starlette.concurrency import run_in_threadpool

from app.schemas.stock import StockDataBase
from app.services import futures_fetcher
from fastapi_cache.decorator import cache

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/list", response_model=dict[str, str])
@cache(expire=86400)  # Cache for 24 hours
async def get_futures_list():
    """
    Get a list of futures symbols from Akshare.
    """
    try:
        futures_df = await run_in_threadpool(ak.futures_display_main_sina)
        return dict(zip(futures_df['symbol'], futures_df['name']))
    except Exception as e:
        logger.error(f"Failed to fetch futures list from Akshare: {str(e)}", exc_info=True)
        return { "ES=F": "E-mini S&P 500", "NQ=F": "E-mini NASDAQ 100" }


@router.get("/{symbol}", response_model=List[StockDataBase])
@cache(expire=900)  # Cache for 15 minutes
async def get_futures_data(
    symbol: str,
    interval: str = Query("daily", enum=["daily", "weekly", "monthly"]),
):
    """
    Get historical data for a specific future using yfinance.
    """
    start_date = (datetime.now() - timedelta(days=10 * 365)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    potential_symbols = [
        symbol.upper(),
        f"{symbol.upper()}.SHF", f"{symbol.upper()}.INE", f"{symbol.upper()}.DCE",
        f"{symbol.upper()}.ZCE", f"{symbol.upper()}.CFX",
    ]
    
    df = None
    last_exception = None

    for s in potential_symbols:
        try:
            fetched_df = await run_in_threadpool(
                futures_fetcher.fetch_futures_from_yfinance,
                symbol=s, start_date=start_date, end_date=end_date, interval=interval,
            )
            if not fetched_df.empty:
                df = fetched_df
                break
        except Exception as e:
            last_exception = e
            logger.warning(f"Could not fetch data for symbol {s}: {e}")
            continue

    if df is None or df.empty:
        logger.error(f"Failed to fetch futures data for {symbol} and its variants: {last_exception}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Failed to fetch data for {symbol} after trying multiple variants.")

    dict_records = df.to_dict("records")
    for record in dict_records:
        record["ts_code"] = symbol # Always return the original symbol
        record["interval"] = interval
        
    records = [StockDataBase.model_validate(record) for record in dict_records]
    return records
