import akshare as ak
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, date

from app.db.session import get_db
from app.schemas.stock import StockInfo
from app.services import data_fetcher

router = APIRouter()

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
def get_all_stock_list(db: Session = Depends(get_db)):
    """
    Get all A-share stocks from the local database cache.
    """
    try:
        # This part can remain as it is, since it's about the stock list, not historical data.
        stocks = data_fetcher.get_all_stocks_list(db)
        if not stocks:
            raise HTTPException(status_code=503, detail="Stock list is empty.")
        return stocks
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"An error occurred: {e}")


def get_trade_date(offset: int = 0) -> str:
    """Helper to get a valid trade date string."""
    return (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")

@router.get("/{stock_code}")
def get_stock_data(
    stock_code: str,
    interval: str = Query("daily", enum=["minute", "5day", "daily", "weekly", "monthly"]),
    trade_date: Optional[date] = Query(None, description="Date for 'minute' or '5day' interval, format YYYY-MM-DD")
):
    """
    Get historical or intraday data for a specific stock using AKShare.
    - **minute**: Intraday minute-level data for a specific `trade_date`.
    - **5day**: Intraday minute-level data for the last 5 trading days up to `trade_date`.
    - **daily, weekly, monthly**: Historical K-line data with moving averages.
    """
    # Convert stock_code from "600519.SH" to "sh600519" or "sz000001" for AKShare
    code_parts = stock_code.split('.')
    if len(code_parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid stock_code format. Expected format: '<code>.<market>' (e.g., '600519.SH')")
    
    ak_code = f"{code_parts[1].lower()}{code_parts[0]}"

    try:
        if interval == "minute":
            if not trade_date:
                trade_date = date.today()
            
            date_str = trade_date.strftime("%Y%m%d")
            df = ak.stock_zh_a_hist_min_em(symbol=code_parts[0], start_date=date_str, end_date=date_str, period='1', adjust='')
            if df.empty:
                return []
            
            df.rename(columns={"时间": "trade_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount", "均价": "avg_price"}, inplace=True)
            return df.to_dict('records')

        elif interval == "5day":
            if not trade_date:
                trade_date = date.today()

            # Get the last 5 trading days
            trade_cal = ak.tool_trade_date_hist_sina()
            trade_cal['trade_date'] = pd.to_datetime(trade_cal['trade_date']).dt.date
            
            # Filter for dates up to the selected trade_date
            recent_dates = trade_cal[trade_cal['trade_date'] <= trade_date].tail(5)
            
            all_dfs = []
            for dt in recent_dates['trade_date']:
                date_str = dt.strftime("%Y%m%d")
                try:
                    df_day = ak.stock_zh_a_hist_min_em(symbol=code_parts[0], start_date=date_str, end_date=date_str, period='1', adjust='')
                    if not df_day.empty:
                        all_dfs.append(df_day)
                except Exception:
                    continue # Ignore days with no data (e.g., holidays)
            
            if not all_dfs:
                return []
                
            df = pd.concat(all_dfs)
            df.rename(columns={"时间": "trade_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount", "均价": "avg_price"}, inplace=True)
            return df.to_dict('records')

        else: # daily, weekly, monthly
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
            adjust_map = "qfq" # 前复权

            # Fetch a long range of data to calculate MAs properly
            start_date = (datetime.now() - timedelta(days=15 * 365)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")

            df = ak.stock_zh_a_hist(symbol=code_parts[0], period=period_map[interval], start_date=start_date, end_date=end_date, adjust=adjust_map)
            if df.empty:
                return []

            # Calculate Moving Averages
            for ma in [5, 10, 20, 60]:
                df[f'ma{ma}'] = df['收盘'].rolling(window=ma).mean()

            df.rename(columns={"日期": "trade_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount"}, inplace=True)
            
            # Convert date format and drop rows with NaN MAs
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
            df.dropna(inplace=True)

            return df.to_dict('records')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from AKShare: {str(e)}")

