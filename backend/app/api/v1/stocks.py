import akshare as ak
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, date
import asyncio

from starlette.concurrency import run_in_threadpool

from app.db.session import get_db
from app.schemas.stock import StockInfo, StockDataInDB
from app.schemas.fundamental import FundamentalDataInDB
from app.schemas.corporate_action import CorporateActionResponse
from app.schemas.annual_earnings import AnnualEarningsInDB
from app.services import data_fetcher
from app.db import models


router = APIRouter()

import logging

logger = logging.getLogger(__name__)

DEFAULT_STOCKS = [
    {"ts_code": "000001.SZ", "name": "平安银行"},
    {"ts_code": "600519.SH", "name": "贵州茅台"},
    {"ts_code": "000300.SH", "name": "沪深300"},
]

@router.get("/list/default", response_model=List[StockInfo])
def get_default_stock_list():
    """
    Get a default list of stocks for the main dashboard.
    """
    return DEFAULT_STOCKS

@router.get("/list/all", response_model=List[StockInfo])
def get_all_stock_list(market_type: str = Query("A_share", enum=["A_share", "US_stock"]), db: Session = Depends(get_db)):
    """
    Get all stocks for a given market type from the local database cache.
    """
    try:
        stocks = data_fetcher.get_all_stocks_list(db, market_type=market_type)
        if not stocks:
            # It's better to return an empty list than an error if the list is just empty
            return []
        return stocks
    except Exception as e:
        logger.error(f"An error occurred while fetching the stock list for {market_type}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"An error occurred while fetching the stock list.")


def get_trade_date(offset: int = 0) -> str:
    """Helper to get a valid trade date string."""
    return (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")

@router.get("/{stock_code}", response_model=List[StockDataBase])
async def get_stock_data(
    stock_code: str,
    interval: str = Query("daily", enum=["minute", "5day", "daily", "weekly", "monthly"]),
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    trade_date: Optional[date] = Query(None, description="Date for 'minute' or '5day' interval, format YYYY-MM-DD")
):
    """
    Get historical or intraday data for a specific stock using AKShare or yfinance.
    This endpoint is asynchronous and uses a thread pool for blocking I/O.
    """
    # Validation: A-share codes must have a market suffix.
    if market_type == "A_share" and '.' not in stock_code:
        raise HTTPException(status_code=400, detail="Invalid A-share stock_code format. Expected format: '<code>.<market>' (e.g., '600519.SH')")

    try:
        # Run the synchronous, blocking function in a thread pool
        df = await run_in_threadpool(
            data_fetcher.fetch_stock_data,
            stock_code=stock_code,
            interval=interval,
            market_type=market_type,
            trade_date=trade_date
        )

        if df.empty:
            return []
        
        # Convert DataFrame to list of dicts and ensure all required fields are present
        records = df.to_dict('records')
        valid_records = []
        for record in records:
            try:
                # Skip records with missing trade_date
                if not record.get('trade_date'):
                    continue
                    
                valid_records.append(StockDataBase(
                    ts_code=stock_code,
                    trade_date=record['trade_date'],
                    open=record.get('open'),
                    high=record.get('high'),
                    low=record.get('low'),
                    close=record.get('close'),
                    pre_close=record.get('pre_close'),
                    change=record.get('change'),
                    pct_chg=record.get('pct_chg'),
                    vol=record.get('vol'),
                    amount=record.get('amount'),
                    interval=interval
                ))
            except Exception as e:
                logger.warning(f"Skipping invalid record: {record}, error: {str(e)}")
                continue
                
        return valid_records

    except Exception as e:
        logger.error(f"Failed to fetch stock data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")


@router.post("/{symbol}/sync", status_code=202)
async def sync_data_for_symbol(symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger a background task to fetch and store fundamental and corporate action data
    for a given stock symbol.
    """
    resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
    if not resolved_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

    background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)
    return {"message": f"Data synchronization for {resolved_symbol} has been started in the background."}


@router.get("/{symbol}/fundamentals", response_model=FundamentalDataInDB)
async def get_fundamental_data(symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Get fundamental data for a given stock symbol.
    Triggers a background sync if data is missing or stale (older than 24 hours).
    """
    resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
    if not resolved_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

    # --- Temporary change for debugging: Always trigger a sync ---
    background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)
    
    db_data = data_fetcher.get_fundamental_data_from_db(db, resolved_symbol)

    if not db_data:
        # If data is not available even after triggering sync, ask user to wait
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": f"Fundamental data for {resolved_symbol} is being synced. Please try again in a moment."}
        )
    
    return db_data


@router.get("/{symbol}/corporate-actions", response_model=CorporateActionResponse)
def get_corporate_actions(symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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
            content={"message": f"Corporate actions for {resolved_symbol} not found. A background sync has been started. Please try again in a moment."}
        )
    
    # Return data that matches the CorporateActionResponse schema
    return {"symbol": resolved_symbol, "actions": actions}

@router.get("/{symbol}/annual-earnings", response_model=List[AnnualEarningsInDB])
async def get_annual_earnings(symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Get annual net profit data for a given stock symbol.
    Triggers a background sync if data is missing or stale (older than 24 hours).
    """
    resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
    if not resolved_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

    db_data = data_fetcher.get_annual_earnings_from_db(db, resolved_symbol)

    # Check if data is stale or missing
    if not db_data or (db_data and (datetime.utcnow() - db_data[0].last_updated) > timedelta(hours=24)):
        background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)
        if not db_data: # If no data at all, inform user it's being synced
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={"message": f"Annual earnings data for {resolved_symbol} is being synced. Please try again in a moment."}
            )
    
    return db_data
