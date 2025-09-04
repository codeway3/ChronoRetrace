import logging
from datetime import datetime, timedelta
from typing import List

import akshare as ak
from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from starlette.concurrency import run_in_threadpool

from app.schemas.stock import StockDataBase
from app.services import futures_fetcher

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
        return dict(zip(futures_df["symbol"], futures_df["name"]))
    except Exception as e:
        logger.error(
            f"Failed to fetch futures list from Akshare: {str(e)}", exc_info=True
        )
        return {"ES=F": "E-mini S&P 500", "NQ=F": "E-mini NASDAQ 100"}


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

    # Try common Yahoo suffix first (e.g., CL=F), then exchange-specific variants
    base = symbol.upper()
    potential_symbols = [
        f"{base}=F",
        base,
        f"{base}.SHF",
        f"{base}.INE",
        f"{base}.DCE",
        f"{base}.ZCE",
        f"{base}.CFX",
    ]

    df = None
    last_exception = None

    # If symbol looks like China futures (e.g., rb2410), fetch directly via Akshare
    if futures_fetcher._is_china_futures_contract(base):  # type: ignore[attr-defined]
        # First try with uppercase base (e.g., RB2410)
        df = await run_in_threadpool(
            futures_fetcher.fetch_china_futures_from_akshare,
            symbol=base,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )
        # If empty, try with the original symbol (could be lowercase like rb2410)
        if df is None or df.empty:
            df = await run_in_threadpool(
                futures_fetcher.fetch_china_futures_from_akshare,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
            )
        if not (df is None or df.empty):
            potential_symbols = [base]
        else:
            # fall back to Yahoo attempts below
            df = None

    if df is None:
        for s in potential_symbols:
            try:
                fetched_df = await run_in_threadpool(
                    futures_fetcher.fetch_futures_from_yfinance,
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
        attempted = ", ".join(potential_symbols)
        msg = f"Failed to fetch futures data for {symbol}. Attempted: {attempted}"
        if last_exception is not None:
            logger.error(f"{msg}: {last_exception}", exc_info=True)
        else:
            logger.error(msg)
        raise HTTPException(
            status_code=404,
            detail=f"No data available for {symbol}. Tried: {attempted}",
        )

    dict_records = df.to_dict("records")
    for record in dict_records:
        record["ts_code"] = symbol  # Always return the original symbol
        record["interval"] = interval

    records = [StockDataBase.model_validate(record) for record in dict_records]
    return records
