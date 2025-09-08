import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from starlette.concurrency import run_in_threadpool

from app.data.fetchers import options_fetcher
from app.schemas.stock import StockDataBase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/expirations/{underlying_symbol}", response_model=tuple[str, ...])
@cache(expire=3600)
async def get_option_expirations(underlying_symbol: str):
    try:
        expirations = await run_in_threadpool(
            options_fetcher.get_expiration_dates, symbol=underlying_symbol
        )
        return expirations
    except Exception as e:
        logger.error(
            f"Failed to fetch expiration dates for {underlying_symbol}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=404,
            detail=f"Could not find expiration dates for symbol '{underlying_symbol}'.",
        ) from e


@router.get("/chain/{underlying_symbol}", response_model=list[Any])
@cache(expire=600)
async def get_option_chain_for_date(
    underlying_symbol: str, expiration_date: str = Query(...)
):
    try:
        chain = await run_in_threadpool(
            options_fetcher.get_option_chain,
            symbol=underlying_symbol,
            expiration_date=expiration_date,
        )
        return chain
    except Exception as e:
        logger.error(
            f"Failed to fetch option chain for {underlying_symbol} on {expiration_date}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch option chain for {underlying_symbol} on {expiration_date}.",
        ) from e


@router.get("/{symbol}", response_model=list[StockDataBase])
@cache(expire=900)
async def get_options_data(
    symbol: str,
    interval: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    window: str = Query(
        "MAX", enum=["3M", "6M", "1Y", "2Y", "5Y", "MAX"], description="历史窗口"
    ),
):
    now = datetime.now()
    if window == "3M":
        start_date = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    elif window == "6M":
        start_date = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    elif window == "1Y":
        start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    elif window == "2Y":
        start_date = (now - timedelta(days=2 * 365)).strftime("%Y-%m-%d")
    elif window == "5Y":
        start_date = (now - timedelta(days=5 * 365)).strftime("%Y-%m-%d")
    else:
        start_date = (now - timedelta(days=10 * 365)).strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        df = await run_in_threadpool(
            options_fetcher.fetch_options_from_yfinance,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )
        if df.empty:
            return []
        dict_records = df.to_dict(orient="records")
        for record in dict_records:
            record["ts_code"] = symbol
            record["interval"] = interval
        return [StockDataBase.model_validate(record) for record in dict_records]
    except Exception as e:
        logger.error(
            f"Failed to fetch options data for {symbol}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch data for {symbol}: {str(e)}"
        ) from e
