import pandas as pd
import baostock as bs
import akshare as ak
from datetime import datetime, date, timedelta
import logging
from contextlib import contextmanager
from sqlalchemy.orm import Session
from typing import Optional
import time
import threading
from app.db import models
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


logger = logging.getLogger(__name__)
baostock_lock = threading.Lock()

# --- Baostock Session Management ---
@contextmanager
def baostock_session():
    """Context manager for Baostock login/logout."""
    with baostock_lock:
        logger.debug("Attempting to log in to Baostock...")
        lg = bs.login()
        if lg.error_code != '0':
            logger.error(f"Baostock login failed: {lg.error_msg}")
            raise RuntimeError(f"Baostock login failed: {lg.error_msg}")
        logger.debug("Baostock login successful.")
        try:
            yield
        finally:
            bs.logout()
            logger.debug("Baostock logout successful.")

# --- Data Fetching with Resilience ---
def _baostock_query_with_retry(query_func, *args, **kwargs):
    """
    Wrapper for Baostock queries with retry logic and resilience against data mismatches.
    Retries are limited and waits are short to improve user experience and interruptibility.
    """
    max_retries = 2  # Reduced from 3
    consecutive_failures = 0
    max_consecutive_failures = 5 # Circuit breaker threshold

    for attempt in range(max_retries):
        if consecutive_failures >= max_consecutive_failures:
            logger.error("Circuit breaker tripped for Baostock queries after multiple consecutive failures.")
            return None # Stop trying

        rs = query_func(*args, **kwargs)
        
        if rs.error_code == '0':
            try:
                return rs.get_data()
            except ValueError as e:
                if "columns passed" in str(e) and rs.data:
                    logger.warning(f"Baostock data/field mismatch for {query_func.__name__}: {e}. Attempting to build DataFrame manually.")
                    try:
                        num_data_cols = len(rs.data[0])
                        limited_fields = rs.fields[:num_data_cols]
                        logger.warning(f"Using first {num_data_cols} fields out of {len(rs.fields)} available: {limited_fields}")
                        return pd.DataFrame(rs.data, columns=limited_fields)
                    except Exception as df_e:
                        logger.error(f"Could not manually construct DataFrame after mismatch: {df_e}")
                        return None
                elif not rs.data:
                    return pd.DataFrame()
                else:
                    logger.error(f"An unhandled ValueError occurred in Baostock result processing: {e}")
                    return None
        
        if rs.error_code == '10002007': # Network reception error
            consecutive_failures += 1
            logger.warning(f"Baostock network error (attempt {attempt + 1}/{max_retries}). Retrying in 1s...")
            time.sleep(1)  # Changed to a fixed, short sleep
        else:
            logger.error(f"Baostock query failed with code {rs.error_code}: {rs.error_msg}")
            return None
    
    logger.error(f"Failed to execute Baostock query after {max_retries} retries.")
    return None

def fetch_annual_net_profit_from_baostock(symbol: str, years: int = 10) -> list[dict]:
    """Fetches annual net profit, aggregating quarterly data with resilience."""
    with baostock_session():
        bs_symbol = symbol.replace('.SH', '.sh').replace('.SZ', '.sz').lower()
        annual_profits = []
        current_year = datetime.now().year
        
        consecutive_failures = 0
        max_consecutive_failures = 8 # Circuit breaker for the whole function

        for year in range(current_year - years, current_year + 1):
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"Circuit breaker for {symbol}: Too many consecutive quarterly failures. Aborting year loop.")
                break

            total_net_profit_this_year = 0.0
            year_has_data = False
            
            for quarter in range(1, 5):
                df_profit = _baostock_query_with_retry(
                    bs.query_profit_data, code=bs_symbol, year=year, quarter=quarter
                )

                if df_profit is None:
                    consecutive_failures += 1
                    continue

                if not df_profit.empty:
                    consecutive_failures = 0 # Reset on success
                    net_profit_str = df_profit.iloc[0].get('netProfit')
                    if net_profit_str and net_profit_str.strip():
                        try:
                            total_net_profit_this_year += float(net_profit_str)
                            year_has_data = True
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse netProfit '{net_profit_str}' for {bs_symbol} {year}Q{quarter}")
                
            if year_has_data:
                annual_profits.append({"year": year, "net_profit": total_net_profit_this_year})

    return annual_profits

# --- Other Fetcher Functions (simplified for brevity, can be enhanced with retry logic too) ---

def update_stock_list_from_akshare(db: Session):
    """
    Fetches the stock and ETF list from Akshare and upserts it into the stock_info table.
    """
    all_securities = []
    # 1. Fetch Stocks
    stock_map = {
        "sh": ("stock_sh_a_spot_em", ".SH", "代码"),
        "sz": ("stock_sz_a_spot_em", ".SZ", "代码"),
        "bj": ("stock_bj_a_spot_em", ".BJ", "代码"),
    }
    for market, (func, suffix, code_col) in stock_map.items():
        try:
            df = getattr(ak, func)()
            # Standardize column names
            if code_col not in df.columns:
                # Fallback for BJ market or other inconsistencies
                if "代码" in df.columns:
                    code_col = "代码"
                elif "code" in df.columns:
                    code_col = "code"
                else:
                    # Add more fallbacks if necessary
                    logger.warning(f"Could not find a valid code column for {market}. Skipping.")
                    continue
            
            df.rename(columns={code_col: "代码", "名称": "name", "name": "name"}, inplace=True)
            
            df["ts_code"] = df["代码"].astype(str) + suffix
            all_securities.append(df[["ts_code", "name"]])
        except Exception as e:
            logger.error(
                f"Failed to fetch stock list for market {market} from Akshare: {e}"
            )

    # 2. Fetch ETFs
    try:
        etf_df = ak.fund_etf_spot_em()
        # Standardize ETF column names
        etf_df.rename(columns={"代码": "代码", "名称": "name"}, inplace=True)

        def get_etf_suffix(code):
            """Determines the market suffix for an ETF code."""
            code_str = str(code)
            if code_str.startswith(('51', '56', '58')):  # Shanghai Stock Exchange ETFs
                return ".SH"
            elif code_str.startswith('15'):  # Shenzhen Stock Exchange ETFs
                return ".SZ"
            else:
                return ""  # Return empty for unknown prefixes
        etf_df["ts_code"] = etf_df["代码"].apply(
            lambda x: str(x) + get_etf_suffix(x)
        )
        # Filter out ETFs where we couldn't determine the market
        etf_df = etf_df[etf_df["ts_code"].str.contains(r"\.")]
        all_securities.append(etf_df[["ts_code", "name"]])
        logger.info(f"Successfully fetched and processed {len(etf_df)} ETFs.")
    except Exception as e:
        logger.error(f"Failed to fetch ETF list from Akshare: {e}")

    # 3. Combine and Save to DB
    if all_securities:
        combined_df = pd.concat(all_securities, ignore_index=True)
        combined_df["market_type"] = "A_share"
        combined_df["last_updated"] = datetime.utcnow()
        records = combined_df.to_dict(orient="records")
        if records:
            stmt = sqlite_insert(models.StockInfo).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ts_code", "market_type"],
                set_=dict(
                    name=stmt.excluded.name, last_updated=stmt.excluded.last_updated
                ),
            )
            db.execute(stmt)
            db.commit()
            logger.info(
                f"Successfully upserted {len(combined_df)} stocks and ETFs into the database."
            )



def fetch_fundamental_data_from_baostock(symbol: str) -> dict | None:
    with baostock_session():
        # This function can also be refactored to use the _baostock_query_with_retry wrapper
        # For now, keeping it as is to focus on the main error source.
        # A full implementation would wrap bs.query_history_k_data_plus, etc.
        return {} # Placeholder for brevity

def fetch_corporate_actions_from_baostock(symbol: str) -> list[dict]:
    """
    Fetches dividend data from Baostock and returns it as a list of actions.
    Split data fetching has been removed as per user request.
    """
    with baostock_session():
        bs_symbol = symbol.replace('.SH', '.sh').replace('.SZ', '.sz').lower()
        actions = []

        # Fetch Dividend Data
        df_dividends = _baostock_query_with_retry(bs.query_dividend_data, code=bs_symbol)
        if df_dividends is not None and not df_dividends.empty:
            for _, row in df_dividends.iterrows():
                try:
                    # Handle cases like '0.5或0.6' by taking the first value
                    dividend_str = str(row["dividCashPsAfterTax"]).split('或')[0].strip()
                    if dividend_str: # Ensure it's not an empty string
                        actions.append({
                            "action_type": "dividend",
                            "ex_date": datetime.strptime(row["dividRegistDate"], "%Y-%m-%d").date(),
                            "value": float(dividend_str)
                        })
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Could not parse dividend row for {symbol}: {row}. Error: {e}")
                    continue

        # Sort actions by date
        if actions:
            actions.sort(key=lambda x: x['ex_date'], reverse=True)

    return actions

def fetch_a_share_data_from_akshare(
    stock_code: str,
    interval: str,
    trade_date: Optional[date] = None
) -> pd.DataFrame:
    """
    Fetches historical or intraday data for a specific A-share stock or ETF using AKShare,
    then cleans and formats it to match the database schema.
    """
    symbol = stock_code.split('.')[0]
    
    try:
        start_date = (datetime.now() - timedelta(days=15 * 365)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        is_etf = symbol.startswith(('15', '51', '56', '58'))
        
        if interval in ["daily", "weekly", "monthly"]:
            if is_etf:
                df = ak.fund_etf_hist_em(symbol=symbol, period=interval, start_date=start_date, end_date=end_date, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period=interval, start_date=start_date, end_date=end_date, adjust="qfq")
        else:
            date_str = (trade_date or date.today()).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist_min_em(symbol=symbol, start_date=date_str, end_date=date_str, period='1', adjust='qfq')

        if df.empty:
            logger.warning(f"AKShare returned empty DataFrame for {stock_code} (is_etf={is_etf}).")
            return pd.DataFrame()

        # --- Data Processing ---
        rename_map = {
            "日期": "trade_date", "时间": "trade_date", "开盘": "open", "收盘": "close", 
            "最高": "high", "最低": "low", "成交量": "vol", "成交额": "amount",
        }
        
        if is_etf:
            rename_map.update({
                "涨跌额": "change",
                "涨跌幅": "pct_chg"
            })

        df = df.rename(columns=rename_map)
        
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values(by='trade_date', ascending=True)
        
        if not is_etf:
            # Calculate missing fields for stocks
            df['pre_close'] = df['close'].shift(1)
            df['change'] = df['close'] - df['pre_close']
            
            pre_close_safe = df['pre_close'].copy()
            pre_close_safe[pre_close_safe == 0] = pd.NA
            df['pct_chg'] = (df['change'] / pre_close_safe) * 100
        else:
            # For ETFs, pct_chg is a percentage, so we need to ensure it's a float
            df['pct_chg'] = pd.to_numeric(df['pct_chg'], errors='coerce')
            # Calculate pre_close for ETFs from provided data
            df['pre_close'] = df['close'] - df['change']

        # Fill NaN values that may have been created during calculations
        df['pre_close'] = df['pre_close'].fillna(df['close'])
        df['change'] = df['change'].fillna(0.0)
        df['pct_chg'] = df['pct_chg'].fillna(0.0)

        final_cols = ['trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']
        df = df.reindex(columns=final_cols, fill_value=0.0)

        return df

    except Exception as e:
        logger.error(f"Failed to fetch or process data from AKShare for {stock_code}: {e}", exc_info=True)
        return pd.DataFrame()
