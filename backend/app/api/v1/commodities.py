import logging
from datetime import datetime, timedelta

import akshare as ak
from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from starlette.concurrency import run_in_threadpool

from app.data.fetchers import commodity_fetcher
from app.schemas.stock import StockDataBase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list", response_model=dict[str, str])
@cache(expire=86400)  # Cache for 24 hours
async def get_commodity_list():
    """
    Get a list of commodity symbols from Akshare.
    """
    try:
        futures_df = await run_in_threadpool(ak.futures_display_main_sina)
        return dict(zip(futures_df["symbol"], futures_df["name"]))
    except Exception as e:
        logger.error(
            f"Failed to fetch commodity list from Akshare: {str(e)}", exc_info=True
        )
        return {"GC=F": "黄金", "SI=F": "白银", "CL=F": "原油"}


@router.get("/{symbol}", response_model=list[StockDataBase])
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

    potential_symbols = [
        symbol.upper(),
        f"{symbol.upper()}.SHF",
        f"{symbol.upper()}.INE",
        f"{symbol.upper()}.DCE",
        f"{symbol.upper()}.ZCE",
        f"{symbol.upper()}.CFX",
    ]

    df = None
    last_exception = None

    for s in potential_symbols:
        try:
            fetched_df = await run_in_threadpool(
                commodity_fetcher.fetch_commodity_from_yfinance,
                symbol=s,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
            )
            if not fetched_df.empty:
                df = fetched_df
                break
        except Exception as e:
            last_exception = e
            logger.warning(f"Could not fetch data for symbol {s}: {e}")
            continue

    if df is None or df.empty:
        logger.error(
            f"Failed to fetch commodity data for {symbol} and its variants: {last_exception}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch data for {symbol} after trying multiple variants.",
        )

    dict_records = df.to_dict(orient="records")
    for record in dict_records:
        record["ts_code"] = symbol  # Always return the original symbol
        record["interval"] = interval

    records = [StockDataBase.model_validate(record) for record in dict_records]
    return records
