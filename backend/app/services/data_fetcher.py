import tushare as ts
import yfinance as yf
import akshare as ak
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from datetime import datetime, timedelta

from app.core.config import settings
from app.db import models

def get_tushare_pro_api():
    """
    Initializes and returns the Tushare pro API client.
    Raises an exception if the token is not configured.
    """
    if not settings.TUSHARE_API_TOKEN or settings.TUSHARE_API_TOKEN == "YOUR_TUSHARE_TOKEN_HERE":
        raise ValueError("Tushare API token is not configured. Please set it in the backend/.env file.")
    return ts.pro_api(settings.TUSHARE_API_TOKEN)

def _convert_ts_code_to_yfinance(ts_code):
    """Converts Tushare code to yfinance ticker format."""
    if ts_code.endswith('.SH'):
        return ts_code.replace('.SH', '.SS')
    return ts_code

def _fetch_from_yfinance(ts_code: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
    """
    Fetches data from yfinance and formats it to match Tushare's output.
    This version is rewritten to be more robust against pandas assignment errors.
    """
    
    yf_ticker = _convert_ts_code_to_yfinance(ts_code)
    
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    
    interval_map = {
        "daily": "1d",
        "weekly": "1wk",
        "monthly": "1mo",
    }
    yf_interval = interval_map.get(interval, "1d") # Default to "1d" if not found

    df = yf.download(yf_ticker, start=start_dt, end=end_dt, interval=yf_interval, auto_adjust=False, progress=False)
    
    if df.empty:
        return pd.DataFrame()

    df.reset_index(inplace=True)

    # Create a new DataFrame to avoid in-place modification errors
    formatted_df = pd.DataFrame()
    formatted_df['ts_code'] = [ts_code] * len(df) # Ensure ts_code is a string column
    formatted_df['trade_date'] = pd.to_datetime(df['Date'])
    formatted_df['open'] = df['Open']
    formatted_df['high'] = df['High']
    formatted_df['low'] = df['Low']
    formatted_df['close'] = df['Close']
    formatted_df['vol'] = df['Volume']
    
    # Safely calculate the rest of the columns
    formatted_df['pre_close'] = formatted_df['close'].shift(1)
    formatted_df['change'] = formatted_df['close'] - formatted_df['pre_close']
    formatted_df['pct_chg'] = (formatted_df['change'] / formatted_df['pre_close']) * 100
    formatted_df['amount'] = formatted_df['close'] * formatted_df['vol'] / 1000

    # Fill NaN values created by shift()
    formatted_df = formatted_df.fillna(0).infer_objects(copy=False)

    return formatted_df

def fetch_and_store_stock_data(db: Session, ts_code: str, start_date: str, end_date: str, interval: str = "daily"):
    """
    Fetch daily, weekly, or monthly stock or index data, trying Tushare first and falling back to yfinance.
    """
    df = pd.DataFrame()
    try:
        pro = get_tushare_pro_api()
        is_index = '300' in ts_code or ts_code.startswith(('000', '399', '999'))
        
        # Tushare API calls for different intervals
        if is_index:
            if interval == "daily":
                df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif interval == "weekly":
                df = pro.index_weekly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif interval == "monthly":
                df = pro.index_monthly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            else:
                raise ValueError(f"Unsupported interval for Tushare index data: {interval}")
        else:
            if interval == "daily":
                df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif interval == "weekly":
                df = pro.weekly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif interval == "monthly":
                df = pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date)
            else:
                raise ValueError(f"Unsupported interval for Tushare stock data: {interval}")
        
        if df.empty: 
            raise ValueError("Empty DataFrame from Tushare")

    except Exception as e:
        # Log the Tushare failure, but don't print to stdout unless it's a critical error
        # print(f"Tushare fetch failed for {ts_code}: {e}. Falling back to yfinance.")
        try:
            df = _fetch_from_yfinance(ts_code, start_date, end_date, interval) # Pass interval to yfinance
        except Exception as yf_e:
            # print(f"yfinance fallback also failed for {ts_code}: {yf_e}")
            raise yf_e

    if df.empty:
        return 0

    try:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['trade_date'] = df['trade_date'].dt.date # Convert to date objects to match SQLAlchemy Date type
        df['interval'] = interval # Add interval column to DataFrame

        data_to_insert = df.to_dict(orient='records')

        stmt = sqlite_insert(models.StockData).values(data_to_insert)
        stmt = stmt.on_conflict_do_nothing(index_elements=['ts_code', 'trade_date', 'interval']) # Update unique constraint

        result = db.execute(stmt)
        # Keep this as it's a useful informational log for successful storage
        print(f"Successfully stored {len(df)} data points for {ts_code} ({interval}).")
        return len(df)
    except Exception as db_e:
        print(f"Database error for {ts_code} ({interval}): {db_e}")
        db.rollback()
        raise db_e

def get_stock_data_from_db(db: Session, ts_code: str, interval: str = "daily"):
    """
    Get all stock data for a given ts_code and interval from the local database.
    """
    result = db.query(models.StockData).filter(
        models.StockData.ts_code == ts_code,
        models.StockData.interval == interval # Add interval filter
    ).order_by(models.StockData.trade_date).all()
    return result

def _update_stock_list_from_tushare(db: Session):
    """
    Fetches the full stock list from Tushare and upserts it into the stock_info table.
    """
    pro = get_tushare_pro_api()
    stocks_df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
    
    if not stocks_df.empty:
        stocks_df['last_updated'] = datetime.utcnow()
        stmt = sqlite_insert(models.StockInfo).values(stocks_df.to_dict(orient='records'))
        stmt = stmt.on_conflict_do_update(index_elements=['ts_code'], set_=dict(name=stmt.excluded.name, last_updated=stmt.excluded.last_updated))
        db.execute(stmt)
        db.commit()
    else:
        raise ValueError("Tushare returned empty stock list.")

def _update_stock_list_from_akshare(db: Session):
    """
    Fetches the stock list from Akshare and upserts it into the stock_info table.
    """
    stock_map = {
        "sh": ("stock_sh_a_spot_em", ".SH"),
        "sz": ("stock_sz_a_spot_em", ".SZ"),
        "bj": ("stock_bj_a_spot_em", ".BJ")
    }
    all_stocks = []
    for market, (func, suffix) in stock_map.items():
        df = getattr(ak, func)()
        df['ts_code'] = df['代码'] + suffix
        df.rename(columns={'名称': 'name'}, inplace=True)
        all_stocks.append(df[['ts_code', 'name']])
    
    if all_stocks:
        stocks_df = pd.concat(all_stocks, ignore_index=True)
        stocks_df['last_updated'] = datetime.utcnow()
        stmt = sqlite_insert(models.StockInfo).values(stocks_df.to_dict(orient='records'))
        stmt = stmt.on_conflict_do_update(index_elements=['ts_code'], set_=dict(name=stmt.excluded.name, last_updated=stmt.excluded.last_updated))
        db.execute(stmt)
        db.commit()

def get_all_stocks_list(db: Session):
    """
    Get all stock list. It serves from a local DB cache.
    If the cache is empty, small, or older than 24 hours, it refreshes from data sources.
    """
    stock_count = db.query(models.StockInfo).count()
    first_record = db.query(models.StockInfo).first()
    
    # Force refresh if the list is empty, only has default seeds, or is stale.
    if stock_count < 100 or (first_record and (datetime.utcnow() - first_record.last_updated) > timedelta(hours=24)):
        try:
            _update_stock_list_from_tushare(db)
        except Exception as e:
            # Log the Tushare failure, but don't print to stdout unless it's a critical error
            # print(f"Tushare failed to provide stock list: {e}. Falling back to Akshare.")
            try:
                _update_stock_list_from_akshare(db)
            except Exception as ak_e:
                # print(f"Akshare fallback also failed: {ak_e}")
                pass # Suppress error if both fail, or log to a proper logging system

    return db.query(models.StockInfo).all()
