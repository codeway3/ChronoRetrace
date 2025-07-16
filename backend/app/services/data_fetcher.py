import yfinance as yf
import pandas as pd
import baostock as bs
import akshare as ak
from typing import Optional
from datetime import datetime, timedelta, date
pd.set_option('future.no_silent_downcasting', True)
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import logging
import httpx
import asyncio
from sqlalchemy.dialects.postgresql import insert as pg_insert
from starlette.concurrency import run_in_threadpool
from io import StringIO

from app.core.config import settings
from app.db import models
from app.db.session import get_db
from app.db.models import FundamentalData, CorporateAction, AnnualEarnings
from app.schemas.fundamental import FundamentalDataCreate
from app.schemas.corporate_action import CorporateActionCreate
from app.schemas.annual_earnings import AnnualEarningsCreate

# Get a logger instance for this module
logger = logging.getLogger(__name__)


def is_a_share_symbol(symbol: str) -> bool:
    """
    Checks if a given symbol is likely an A-share stock symbol based on common patterns.
    A-share symbols are typically 6-digit numbers, sometimes with .SH/.SZ/.BJ suffix.
    """
    print(f"DEBUG: is_a_share_symbol called with symbol: {symbol}") # Added debug print
    # Remove market suffix if present for initial digit check
    if '.' in symbol:
        code_part = symbol.split('.')[0]
    else:
        code_part = symbol

    # Check if it's a 6-digit number
    if len(code_part) == 6 and code_part.isdigit():
        print(f"DEBUG: is_a_share_symbol returning True for code_part: {code_part}") # Added debug print
        # Further refine by common A-share prefixes if needed, but 6 digits is a strong indicator
        # For example, 000xxx, 300xxx, 600xxx, 688xxx
        return True
    print(f"DEBUG: is_a_share_symbol returning False for code_part: {code_part}") # Added debug print
    return False

def _convert_ts_code_to_yfinance(ts_code):
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
        try:
            df = _fetch_from_yfinance(ts_code, start_date, end_date, interval) # Pass interval to yfinance
        except Exception as yf_e:
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
        logger.info(f"Successfully stored {len(df)} data points for {ts_code} ({interval}).")
        return len(df)
    except Exception as db_e:
        logger.error(f"Database error for {ts_code} ({interval}): {db_e}")
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
    
    if stock_count < 100 or (first_record and (datetime.utcnow() - first_record.last_updated) > timedelta(hours=24)):
        try:
            _update_stock_list_from_tushare(db)
        except Exception as e:
            try:
                _update_stock_list_from_akshare(db)
            except Exception as ak_e:
                pass 

    return db.query(models.StockInfo).all()

def _fetch_fundamental_data_from_baostock(symbol: str) -> dict | None:
    """
    Fetches and calculates fundamental data for A-share stock from Baostock.
    This version is simplified and more robust, with detailed logging.
    """
    logger.info(f"DEBUG: --- Starting fundamental data fetch for {symbol} ---")
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"DEBUG: Baostock login failed: {lg.error_msg}")
        return None

    try:
        bs_symbol = symbol.replace('.SH', '.sh').replace('.SZ', '.sz').lower()
        eps, pe_ratio, market_cap, dividend_yield = None, None, None, None
        
        end_date = datetime.now()
        start_date_k = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
        
        logger.info(f"DEBUG: Querying K data for {bs_symbol} from {start_date_k} to {end_date.strftime('%Y-%m-%d')}")
        rs_k = bs.query_history_k_data_plus(
            bs_symbol, "date,close",
            start_date=start_date_k, end_date=end_date.strftime('%Y-%m-%d'),
            frequency="d", adjustflag="3"
        )
        logger.info(f"DEBUG: Baostock K data response code: {rs_k.error_code}, msg: {rs_k.error_msg}")

        df_k = rs_k.get_data()
        latest_close = None
        if not df_k.empty:
            latest_k_data = df_k.iloc[-1]
            logger.info(f"DEBUG: Latest K data from Baostock: \n{latest_k_data.to_string()}")

            def to_float(value):
                return float(value) if value and value.strip() and value != '' else None

            pe_ratio = to_float(latest_k_data.get('peTTM'))
            market_cap = to_float(latest_k_data.get('totalMv'))
            if market_cap: market_cap *= 10000
            
            eps = to_float(latest_k_data.get('epsTTM'))
            latest_close = to_float(latest_k_data.get('close'))
        else:
            logger.warning(f"DEBUG: K data from Baostock is empty for {bs_symbol}.")

        if latest_close and latest_close > 0:
            start_year = str(end_date.year - 2)
            logger.info(f"DEBUG: Querying dividend data for {bs_symbol} since year {start_year}")
            rs_dividend = bs.query_dividend_data(code=bs_symbol, year=start_year, yearType="report")
            logger.info(f"DEBUG: Baostock dividend data response code: {rs_dividend.error_code}, msg: {rs_dividend.error_msg}")
            
            df_dividend = rs_dividend.get_data()
            if not df_dividend.empty:
                logger.info(f"DEBUG: Raw dividend data from Baostock: \n{df_dividend.head().to_string()}")
                df_dividend['dividCashPsAfterTax'] = pd.to_numeric(df_dividend['dividCashPsAfterTax'], errors='coerce').fillna(0)
                df_dividend['dividPayDate'] = pd.to_datetime(df_dividend['dividPayDate'], errors='coerce')
                
                last_year_date = end_date - timedelta(days=365)
                recent_dividends = df_dividend[df_dividend['dividPayDate'] >= last_year_date]
                
                if not recent_dividends.empty:
                    total_dividends = recent_dividends['cashDivTax'].sum()
                    dividend_yield = (total_dividends / latest_close) * 100
            else:
                logger.warning(f"DEBUG: Dividend data from Baostock is empty for {bs_symbol}.")

        final_data = {
            "symbol": symbol,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "dividend_yield": dividend_yield,
            "eps": eps,
            "beta": None,
            "gross_profit_margin": None,
            "net_profit_margin": None,
            "roe": None,
            "revenue_growth_rate": None,
            "net_profit_growth_rate": None,
            "debt_to_asset_ratio": None,
            "current_ratio": None,
        }

        # Fetch Profit Data
        logger.info(f"DEBUG: Querying profit data for {bs_symbol}")
        rs_profit = bs.query_profit_data(code=bs_symbol, year=end_date.year, quarter=end_date.month // 3 + (1 if end_date.month % 3 > 0 else 0))
        df_profit = rs_profit.get_data()
        logger.info(f"DEBUG: Raw profit data from Baostock for {bs_symbol}: \n{df_profit.to_string()}") # Added logging
        if not df_profit.empty:
            latest_profit_data = df_profit.iloc[0] # Assuming latest is first
            final_data["gross_profit_margin"] = to_float(latest_profit_data.get('grossSaleRate')) # 销售毛利率
            final_data["net_profit_margin"] = to_float(latest_profit_data.get('netProfitRatio')) # 销售净利率
            final_data["roe"] = to_float(latest_profit_data.get('roeAvg')) # 净资产收益率
            logger.info(f"DEBUG: Latest profit data from Baostock: {final_data['gross_profit_margin']}, {final_data['net_profit_margin']}, {final_data['roe']}")
        else:
            logger.warning(f"DEBUG: Profit data from Baostock is empty for {bs_symbol}.")

        # Fetch Growth Data
        logger.info(f"DEBUG: Querying growth data for {bs_symbol}")
        rs_growth = bs.query_growth_data(code=bs_symbol, year=end_date.year, quarter=end_date.month // 3 + (1 if end_date.month % 3 > 0 else 0))
        df_growth = rs_growth.get_data()
        logger.info(f"DEBUG: Raw growth data from Baostock for {bs_symbol}: \n{df_growth.to_string()}") # Added logging
        if not df_growth.empty:
            latest_growth_data = df_growth.iloc[0]
            final_data["revenue_growth_rate"] = to_float(latest_growth_data.get('yoy_revenue')) # 营业收入同比增长率
            final_data["net_profit_growth_rate"] = to_float(latest_growth_data.get('yoy_profit')) # 净利润同比增长率
            logger.info(f"DEBUG: Latest growth data from Baostock: {final_data['revenue_growth_rate']}, {final_data['net_profit_growth_rate']}")
        else:
            logger.warning(f"DEBUG: Growth data from Baostock is empty for {bs_symbol}.")

        # Fetch Balance Data (for solvency)
        logger.info(f"DEBUG: Querying balance data for {bs_symbol}")
        rs_balance = bs.query_balance_data(code=bs_symbol, year=end_date.year, quarter=end_date.month // 3 + (1 if end_date.month % 3 > 0 else 0))
        df_balance = rs_balance.get_data()
        logger.info(f"DEBUG: Raw balance data from Baostock for {bs_symbol}: \n{df_balance.to_string()}") # Added logging
        if not df_balance.empty:
            latest_balance_data = df_balance.iloc[0]
            final_data["debt_to_asset_ratio"] = to_float(latest_balance_data.get('assetLiabilityRatio')) # 资产负债率
            final_data["current_ratio"] = to_float(latest_balance_data.get('currentRatio')) # 流动比率
            logger.info(f"DEBUG: Latest balance data from Baostock: {final_data['debt_to_asset_ratio']}, {final_data['current_ratio']}")
        else:
            logger.warning(f"DEBUG: Balance data from Baostock is empty for {bs_symbol}.")
        logger.info(f"DEBUG: --- Final processed data for {symbol}: {final_data} ---")
        return final_data

    except Exception as e:
        logger.error(f"DEBUG: Exception in _fetch_fundamental_data_from_baostock for {symbol}: {e}", exc_info=True)
        return None
    finally:
        bs.logout()
        logger.info(f"DEBUG: Baostock logged out for {symbol}.")

def _fetch_corporate_actions_from_baostock(symbol: str) -> pd.DataFrame:
    """
    Fetches corporate actions (dividends) for A-share stock from Baostock.
    Returns a DataFrame formatted for store_corporate_actions.
    """
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"Baostock login failed: {lg.error_msg}")
        return pd.DataFrame()

    try:
        bs_symbol = symbol.replace('.SH', '.sh').replace('.SZ', '.sz').lower()
        
        rs_dividend = bs.query_dividend_data(code=bs_symbol)
        df_dividends = rs_dividend.get_data()

        if df_dividends.empty:
            logger.info(f"Baostock: No dividend data found for {symbol}")
            return pd.DataFrame()

        # Use correct column names from Baostock response
        df_dividends.rename(columns={
            'dividRegistDate': 'timestamp',      #股权登记日
            'dividCashPsAfterTax': 'dividend_amount' #税后现金分红
        }, inplace=True)

        # Ensure 'timestamp' and 'dividend_amount' columns exist after renaming
        if 'timestamp' not in df_dividends.columns or 'dividend_amount' not in df_dividends.columns:
             raise KeyError("Failed to rename required columns. Check Baostock API response.")

        # Convert timestamp to datetime objects, coercing errors
        df_dividends['timestamp'] = pd.to_datetime(df_dividends['timestamp'], errors='coerce')
        df_dividends.dropna(subset=['timestamp'], inplace=True) # Drop rows where date conversion failed

        # Convert dividend_amount to numeric, coercing errors
        df_dividends['dividend_amount'] = pd.to_numeric(df_dividends['dividend_amount'], errors='coerce')
        
        # Add split_coefficient column, assuming no split data from this API
        df_dividends['split_coefficient'] = 1.0

        # Filter for actual dividends (value > 0)
        df_dividends = df_dividends[df_dividends['dividend_amount'] > 0]

        return df_dividends[['timestamp', 'dividend_amount', 'split_coefficient']]
            
    except Exception as e:
        logger.error(f"Error fetching corporate actions from Baostock for {symbol}: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        bs.logout()

def get_corporate_actions_from_db(db: Session, symbol: str) -> list[models.CorporateAction]:
    """
    Get all corporate actions for a given symbol from the database.
    """
    return db.query(models.CorporateAction).filter(models.CorporateAction.symbol == symbol).order_by(models.CorporateAction.ex_date).all()


async def _internal_async_sync(symbol: str):
    """
    The actual async implementation of the sync task.
    This version is focused on fetching data for A-shares using Baostock.
    """
    logger.info(f"BACKGROUND_TASK: Starting data sync for A-share symbol: {symbol}")
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # Fetch and store A-share fundamental data
        logger.info(f"BACKGROUND_TASK: [{symbol}] Fetching fundamental data from Baostock...")
        fund_data_bs = await run_in_threadpool(_fetch_fundamental_data_from_baostock, symbol)
        if fund_data_bs:
            await run_in_threadpool(store_fundamental_data, db, symbol, fund_data_bs)
            logger.info(f"BACKGROUND_TASK_SUCCESS: [{symbol}] Successfully synced fundamental data.")
        else:
            logger.warning(f"BACKGROUND_TASK: [{symbol}] No fundamental data found from Baostock.")

        # Fetch and store A-share corporate actions
        logger.info(f"BACKGROUND_TASK: [{symbol}] Fetching corporate actions from Baostock...")
        corporate_actions_df = await run_in_threadpool(_fetch_corporate_actions_from_baostock, symbol)
        if not corporate_actions_df.empty:
            count = await run_in_threadpool(store_corporate_actions, db, symbol, corporate_actions_df)
            logger.info(f"BACKGROUND_TASK_SUCCESS: [{symbol}] Successfully synced {count} corporate actions.")
        else:
            logger.warning(f"BACKGROUND_TASK: [{symbol}] No corporate actions found from Baostock.")

        # Fetch and store A-share annual earnings
        logger.info(f"BACKGROUND_TASK: [{symbol}] Fetching annual earnings from Baostock...")
        annual_earnings_data = await run_in_threadpool(_fetch_annual_net_profit_from_baostock, symbol)
        if annual_earnings_data:
            count = await run_in_threadpool(store_annual_earnings, db, symbol, annual_earnings_data)
            logger.info(f"BACKGROUND_TASK_SUCCESS: [{symbol}] Successfully synced {count} annual earnings records.")
        else:
            logger.warning(f"BACKGROUND_TASK: [{symbol}] No annual earnings data found from Baostock.")
            
    except Exception as e:
        logger.error(f"BACKGROUND_TASK_FAIL: [{symbol}] Failed to sync A-share data: {e}", exc_info=True)
    finally:
        logger.info(f"BACKGROUND_TASK: [{symbol}] Closing database session.")
        next(db_gen, None) # Ensure the session is closed


async def sync_financial_data(symbol: str):
    """
    Asynchronous background task to fetch and store financial data.
    """
    try:
        # Currently, this function is specialized for A-shares via Baostock.
        # It can be extended for other markets if needed.
        await _internal_async_sync(symbol)
    except Exception as e:
        logger.error(f"SYNC_TASK_ERROR for {symbol}: {e}", exc_info=True)


def fetch_stock_data_from_akshare(
    stock_code: str,
    interval: str,
    trade_date: Optional[date] = None
) -> pd.DataFrame:
    """
    Fetches historical or intraday data for a specific stock using AKShare.
    This is a blocking I/O function and should be run in a thread pool.
    """
    code_parts = stock_code.split('.')
    # ak_code = f"{code_parts[1].lower()}{code_parts[0]}" # Not used directly

    try:
        if interval == "minute":
            if not trade_date:
                trade_date = date.today()
            
            date_str = trade_date.strftime("%Y%m%d")
            df = ak.stock_zh_a_hist_min_em(symbol=code_parts[0], start_date=date_str, end_date=date_str, period='1', adjust='')
            if df.empty:
                return pd.DataFrame()
            
            df.rename(columns={"时间": "trade_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount", "均价": "avg_price"}, inplace=True)
            return df

        elif interval == "5day":
            if not trade_date:
                trade_date = date.today()

            trade_cal = ak.tool_trade_date_hist_sina()
            trade_cal['trade_date'] = pd.to_datetime(trade_cal['trade_date']).dt.date
            
            recent_dates = trade_cal[trade_cal['trade_date'] <= trade_date].tail(5)
            
            all_dfs = []
            for dt in recent_dates['trade_date']:
                date_str = dt.strftime("%Y%m%d")
                try:
                    df_day = ak.stock_zh_a_hist_min_em(symbol=code_parts[0], start_date=date_str, end_date=date_str, period='1', adjust='')
                    if not df_day.empty:
                        all_dfs.append(df_day)
                except Exception:
                    continue
            
            if not all_dfs:
                return pd.DataFrame()
                
            df = pd.concat(all_dfs)
            df.rename(columns={"时间": "trade_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount", "均价": "avg_price"}, inplace=True)
            return df

        else: # daily, weekly, monthly
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
            adjust_map = "qfq"

            start_date = (datetime.now() - timedelta(days=15 * 365)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")

            df = ak.stock_zh_a_hist(symbol=code_parts[0], period=period_map[interval], start_date=start_date, end_date=end_date, adjust=adjust_map)
            if df.empty:
                return pd.DataFrame()

            for ma in [5, 10, 20, 60]:
                df[f'ma{ma}'] = df['收盘'].rolling(window=ma).mean()

            df.rename(columns={"日期": "trade_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount"}, inplace=True)
            
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
            df.dropna(inplace=True)

            return df

    except Exception as e:
        logger.error(f"Failed to fetch data from AKShare for {stock_code}: {str(e)}")
        # Re-raise the exception to be handled by the caller
        raise e


def get_fundamental_data_from_db(db: Session, symbol: str) -> Optional[models.FundamentalData]:
    """
    Get fundamental data for a given symbol from the database.
    """
    return db.query(models.FundamentalData).filter(models.FundamentalData.symbol == symbol).first()



def store_annual_earnings(db: Session, symbol: str, annual_earnings_data: list[dict]):
    """
    Stores or updates annual earnings data in the database.
    """
    if not annual_earnings_data:
        return 0

    earnings_to_insert = []
    for item in annual_earnings_data:
        earnings_to_insert.append({
            "symbol": symbol,
            "year": item["year"],
            "net_profit": item["net_profit"],
            "last_updated": datetime.utcnow(),
        })

    if db.bind.dialect.name == 'sqlite':
        stmt = sqlite_insert(models.AnnualEarnings).values(earnings_to_insert)
        stmt = stmt.on_conflict_do_update(
            index_elements=['symbol', 'year'],
            set_=dict(net_profit=stmt.excluded.net_profit, last_updated=stmt.excluded.last_updated)
        )
    else:
        stmt = pg_insert(models.AnnualEarnings).values(earnings_to_insert)
        stmt = stmt.on_conflict_do_update(
            index_elements=['symbol', 'year'],
            set_=dict(net_profit=stmt.excluded.net_profit, last_updated=stmt.excluded.last_updated)
        )
    
    result = db.execute(stmt)
    db.commit()
    return result.rowcount

def get_annual_earnings_from_db(db: Session, symbol: str) -> list[models.AnnualEarnings]:
    """
    Get all annual earnings data for a given symbol from the database.
    """
    return db.query(models.AnnualEarnings).filter(models.AnnualEarnings.symbol == symbol).order_by(models.AnnualEarnings.year).all()


def _fetch_annual_net_profit_from_baostock(symbol: str, years: int = 10) -> list[dict]:
    """
    Fetches annual net profit data for A-share stock from Baostock by aggregating quarterly data.
    """
    logger.info(f"DEBUG: Fetching annual net profit for {symbol} for last {years} years.")
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"DEBUG: Baostock login failed: {lg.error_msg}")
        return []

    try:
        bs_symbol = symbol.replace('.SH', '.sh').replace('.SZ', '.sz').lower()
        annual_profits = []
        current_year = datetime.now().year

        for year in range(current_year - years + 1, current_year + 1):
            total_net_profit_this_year = 0.0
            quarters_found = 0
            for quarter in range(1, 5): # Iterate through quarters 1, 2, 3, 4
                rs_profit = bs.query_profit_data(code=bs_symbol, year=year, quarter=quarter)
                df_profit = rs_profit.get_data()
                
                if not df_profit.empty:
                    # Baostock's profit data has 'netProfit' field
                    net_profit_str = df_profit.iloc[0].get('netProfit')
                    if net_profit_str and net_profit_str.strip():
                        try:
                            net_profit = float(net_profit_str)
                            total_net_profit_this_year += net_profit
                            quarters_found += 1
                        except ValueError:
                            logger.warning(f"DEBUG: Could not convert netProfit '{net_profit_str}' to float for {bs_symbol} {year}Q{quarter}")
                else:
                    logger.info(f"DEBUG: No profit data for {bs_symbol} {year}Q{quarter}")
            
            if quarters_found > 0:
                annual_profits.append({"year": year, "net_profit": total_net_profit_this_year})
            else:
                logger.warning(f"DEBUG: No profit data found for {bs_symbol} in year {year}")

        logger.info(f"DEBUG: Annual net profits for {symbol}: {annual_profits}")
        return annual_profits

    except Exception as e:
        logger.error(f"DEBUG: Exception in _fetch_annual_net_profit_from_baostock for {symbol}: {e}", exc_info=True)
        return []
    finally:
        bs.logout()
        logger.info(f"DEBUG: Baostock logged out for {symbol}.")

def resolve_symbol(db: Session, symbol: str) -> Optional[str]:
    """
    Resolves a potentially incomplete stock symbol to its full ts_code.
    e.g., "000001" -> "000001.SZ"
    """
    logger.info(f"DEBUG: resolve_symbol received: {symbol}") # Added log
    if '.' in symbol:
        # Assume it's already a full ts_code
        logger.info(f"DEBUG: resolve_symbol returning (already full ts_code): {symbol}") # Added log
        return symbol
    
    # Search for the code in our stock list
    # This query is case-insensitive for the market suffix (e.g. .sz or .SZ)
    stock_info = db.query(models.StockInfo).filter(models.StockInfo.ts_code.ilike(f"{symbol}.%")).first()

    if stock_info:
        logger.info(f"DEBUG: resolve_symbol returning (resolved from DB): {stock_info.ts_code}") # Added log
        return stock_info.ts_code
    
    logger.warning(f"DEBUG: resolve_symbol could not resolve: {symbol}") # Added log
    return None
