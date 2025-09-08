import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.data.managers import data_manager as data_fetcher
from app.infrastructure.database.session import get_db
from app.schemas.annual_earnings import AnnualEarningsInDB
from app.schemas.corporate_action import CorporateActionResponse
from app.schemas.fundamental import FundamentalDataInDB
from app.schemas.stock import StockDataBase, StockInfo

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/list/all", response_model=list[StockInfo])
@cache(expire=86400)  # Cache for 24 hours
def get_all_stock_list(
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    db: Session = Depends(get_db),
):
    """
    Get all stocks for a given market type from the local database cache.
    This endpoint is cached for 24 hours.
    """
    try:
        stocks = data_fetcher.get_all_stocks_list(db, market_type=market_type)
        if not stocks:
            # It's better to return an empty list than an error if the list is just empty
            return []
        return stocks
    except Exception as e:
        logger.error(
            f"An error occurred while fetching the stock list for {market_type}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=503, detail="An error occurred while fetching the stock list."
        ) from e


@router.post("/list/refresh", status_code=200)
async def refresh_stock_list(
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    db: Session = Depends(get_db),
):
    """
    Force a refresh of the stock list for a given market type and clear the cache.
    """
    try:
        logger.info(f"Force refreshing stock list for {market_type}...")
        # This will call the updated function in a_share_fetcher.py
        await run_in_threadpool(
            data_fetcher.force_update_stock_list, db, market_type=market_type
        )

        # Clear the cache for the get_all_stock_list endpoint
        await FastAPICache.clear(namespace="fastapi-cache")
        logger.info(f"Cache cleared and stock list for {market_type} refreshed.")

        return {"message": f"Successfully refreshed stock list for {market_type}."}
    except Exception as e:
        logger.error(
            f"An error occurred during force refresh for {market_type}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="An error occurred during the refresh process."
        ) from e


def get_trade_date(offset: int = 0) -> str:
    """Helper to get a valid trade date string."""
    return (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")


@router.get("/{stock_code}", response_model=list[StockDataBase])
@cache(expire=900)  # Cache for 15 minutes
async def get_stock_data(
    stock_code: str,
    interval: str = Query(
        "daily", enum=["minute", "5day", "daily", "weekly", "monthly"]
    ),
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    trade_date: date | None = Query(
        None, description="Date for 'minute' or '5day' interval, format YYYY-MM-DD"
    ),
):
    """
    Get historical or intraday data for a specific stock using AKShare or yfinance.
    This endpoint is asynchronous and uses a thread pool for blocking I/O.
    """
    # Validation: A-share codes must have a market suffix.
    if market_type == "A_share" and "." not in stock_code:
        raise HTTPException(
            status_code=400,
            detail="Invalid A-share stock_code format. Expected format: '<code>.<market>' (e.g., '600519.SH')",
        )

    try:
        # Run the synchronous, blocking function in a thread pool
        df = await run_in_threadpool(
            data_fetcher.fetch_stock_data,
            stock_code=stock_code,
            interval=interval,
            market_type=market_type,
            trade_date=trade_date,
        )

        if df.empty:
            return []

        # Convert DataFrame to list of Pydantic models
        # This explicitly validates and includes the MA fields
        # Also, add ts_code and interval to each record for frontend consistency
        dict_records = df.to_dict(orient="records")
        for record in dict_records:
            record["ts_code"] = stock_code
            record["interval"] = interval

        records = [StockDataBase.model_validate(record) for record in dict_records]

        return records

    except Exception as e:
        logger.error(f"Failed to fetch stock data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}") from e


@router.post("/{symbol}/sync", status_code=202)
async def sync_data_for_symbol(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Trigger a background task to fetch and store fundamental and corporate action data
    for a given stock symbol.
    """
    resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
    if not resolved_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

    background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)
    return {
        "message": f"Data synchronization for {resolved_symbol} has been started in the background."
    }


@router.get("/{symbol}/fundamentals", response_model=FundamentalDataInDB)
async def get_fundamental_data(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Get fundamental data for a given stock symbol.
    Triggers a background sync if data is missing or stale (older than 24 hours).
    """
    resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
    if not resolved_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

    db_data = data_fetcher.get_fundamental_data_from_db(db, resolved_symbol)

    # Check if data is stale or missing
    if not db_data or (
        db_data and (datetime.utcnow() - db_data.last_updated) > timedelta(hours=24)  # type: ignore
    ):
        background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)
        if not db_data:  # If no data at all, inform user it's being synced
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": f"Fundamental data for {resolved_symbol} is being synced. Please try again in a moment."
                },
            )

    return db_data


@router.get("/{symbol}/corporate-actions", response_model=CorporateActionResponse)
def get_corporate_actions(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Get all corporate actions for a given stock symbol.
    Triggers a background sync if data is missing.
    """
    resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
    if not resolved_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

    actions = data_fetcher.get_corporate_actions_from_db(db, resolved_symbol)

    if not actions:
        background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": f"Corporate actions for {resolved_symbol} not found. A background sync has been started. Please try again in a moment."
            },
        )

    # Return data that matches the CorporateActionResponse schema
    return {"symbol": resolved_symbol, "actions": actions}


@router.get("/{symbol}/annual-earnings", response_model=list[AnnualEarningsInDB])
async def get_annual_earnings(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Get annual net profit data for a given stock symbol.
    Triggers a background sync if data is missing or stale (older than 24 hours).
    """
    resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
    if not resolved_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

    db_data = data_fetcher.get_annual_earnings_from_db(db, resolved_symbol)

    # Check if data is stale or missing
    if not db_data or (
        db_data and (datetime.utcnow() - db_data[0].last_updated) > timedelta(hours=24)  # type: ignore
    ):
        background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)
        if not db_data:  # If no data at all, inform user it's being synced
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": f"Annual earnings data for {resolved_symbol} is being synced. Please try again in a moment."
                },
            )

    return db_data
