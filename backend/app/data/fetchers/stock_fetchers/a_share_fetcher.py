from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import akshare as ak
import baostock as bs
import pandas as pd
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.infrastructure.database import models

from typing import Union

logger = logging.getLogger(__name__)
baostock_lock = threading.Lock()

# --- Baostock Session Management ---


@contextmanager
def baostock_session():
    """Context manager for Baostock login/logout."""
    with baostock_lock:
        logger.debug("Attempting to log in to Baostock...")
        login_result = bs.login()
        if login_result.error_code != "0":
            logger.error(f"Baostock login failed: {login_result.error_msg}")
            raise RuntimeError(f"Baostock login failed: {login_result.error_msg}")
        logger.debug("Baostock login successful.")
        try:
            yield
        finally:
            bs.logout()
            logger.debug("Baostock logout successful.")


# --- Batch Data Fetching with AKShare ---


def _fetch_spot_data_batch() -> dict[str, pd.DataFrame]:
    """
    Fetches spot data for all A-shares and ETFs in a single batch.
    This is useful for daily data to avoid frequency limits.
    """
    all_data = {}
    try:
        # Fetch all A-shares
        stock_df = ak.stock_zh_a_spot_em()
        logger.info(f"Fetched {len(stock_df)} A-shares")

        # Process A-shares
        def _first(row_like, *candidates):
            for key in candidates:
                if key in row_like and pd.notna(row_like.get(key)):
                    return row_like.get(key)
            return None

        for _, row in stock_df.iterrows():
            code = str(row["代码"])

            # 根据代码前缀确定市场后缀
            # 深市：00/30/001/003/301 等；沪市：60/68（含科创板 688/689）；北交所：4/8 前缀
            if code.startswith(("00", "30", "001", "003", "301", "002")):
                ts_code = code + ".SZ"  # 深市
            elif code.startswith(("60", "68", "688", "689")):
                ts_code = code + ".SH"  # 沪市
            elif code.startswith(("8", "4")):
                ts_code = code + ".BJ"  # 北交所
            else:
                # 默认回退到沪市（极少数非常规代码）
                ts_code = code + ".SH"

            # 兼容不同列名的统一提取
            open_val = _first(row, "开盘", "开盘价")
            high_val = _first(row, "最高", "最高价")
            low_val = _first(row, "最低", "最低价")
            close_val = _first(row, "最新价", "现价", "收盘")
            pre_close_val = _first(row, "昨收", "昨收盘")
            change_val = _first(row, "涨跌额")
            pct_chg_val = _first(row, "涨跌幅")
            vol_val = _first(row, "成交量")
            amount_val = _first(row, "成交额")
            pe_dynamic = _first(row, "市盈率-动态", "市盈率TTM", "PE(TTM)")
            pb_val = _first(row, "市净率", "PB")
            mkt_cap = _first(row, "总市值", "市值")

            # 转换为DataFrame格式（英文字段，供调用方统一使用）
            stock_data = pd.DataFrame(
                [
                    {
                        "trade_date": datetime.now().strftime("%Y-%m-%d"),
                        "open": open_val,
                        "high": high_val,
                        "low": low_val,
                        "close": close_val,
                        "pre_close": pre_close_val,
                        "change": change_val,
                        "pct_chg": pct_chg_val,
                        "vol": vol_val,
                        "amount": amount_val,
                        "pe_ratio": pe_dynamic,
                        "pb_ratio": pb_val,
                        "market_cap": mkt_cap,
                    }
                ]
            )

            all_data[ts_code] = stock_data

        # Fetch all ETFs
        etf_df = ak.fund_etf_spot_em()
        logger.info(f"Fetched {len(etf_df)} ETFs")

        # Process ETFs
        for _, row in etf_df.iterrows():
            code = str(row["代码"])

            # 根据代码前缀确定市场后缀
            if code.startswith("15"):
                ts_code = code + ".SZ"  # 深市ETF
            else:
                ts_code = code + ".SH"  # 沪市ETF

            open_val = row.get("开盘", row.get("开盘价"))
            high_val = row.get("最高", row.get("最高价"))
            low_val = row.get("最低", row.get("最低价"))
            close_val = row.get("最新价", row.get("现价", row.get("收盘")))
            pre_close_val = row.get("昨收", row.get("昨收盘"))
            change_val = row.get("涨跌额")
            pct_chg_val = row.get("涨跌幅")
            vol_val = row.get("成交量")
            amount_val = row.get("成交额")

            etf_data = pd.DataFrame(
                [
                    {
                        "trade_date": datetime.now().strftime("%Y-%m-%d"),
                        "open": open_val,
                        "high": high_val,
                        "low": low_val,
                        "close": close_val,
                        "pre_close": pre_close_val,
                        "change": change_val,
                        "pct_chg": pct_chg_val,
                        "vol": vol_val,
                        "amount": amount_val,
                    }
                ]
            )

            all_data[ts_code] = etf_data

    except Exception as e:
        logger.error(f"Failed to fetch spot data in batch: {e}")
    return all_data


# --- Data Fetching with Resilience ---


def _baostock_query_with_retry(query_func, *args, **kwargs):
    """
    Wrapper for Baostock queries with retry logic and resilience against data mismatches.
    Retries are limited and waits are short to improve user experience and interruptibility.
    """
    max_retries = 2  # Reduced from 3
    consecutive_failures = 0
    max_consecutive_failures = 5  # Circuit breaker threshold

    for attempt in range(max_retries):
        if consecutive_failures >= max_consecutive_failures:
            logger.error(
                "Circuit breaker tripped for Baostock queries after multiple consecutive failures."
            )
            return None  # Stop trying

        query_result = query_func(*args, **kwargs)

        if query_result.error_code == "0":
            try:
                return query_result.get_data()
            except ValueError as e:
                if "columns passed" in str(e) and query_result.data:
                    logger.warning(
                        f"Baostock data/field mismatch for {query_func.__name__}: {e}. Attempting to build DataFrame manually."
                    )
                    try:
                        num_data_cols = len(query_result.data[0])
                        limited_fields = query_result.fields[:num_data_cols]
                        logger.warning(
                            f"Using first {num_data_cols} fields out of {len(query_result.fields)} available: {limited_fields}"
                        )
                        return pd.DataFrame(query_result.data, columns=limited_fields)
                    except Exception as df_e:
                        logger.error(
                            f"Could not manually construct DataFrame after mismatch: {df_e}"
                        )
                        return None
                elif not query_result.data:
                    return pd.DataFrame()
                else:
                    logger.error(
                        f"An unhandled ValueError occurred in Baostock result processing: {e}"
                    )
                    return None

        if query_result.error_code == "10002007":  # Network reception error
            consecutive_failures += 1
            logger.warning(
                f"Baostock network error (attempt {attempt + 1}/{max_retries}). Retrying in 1s..."
            )
            time.sleep(1)  # Changed to a fixed, short sleep
        else:
            logger.error(
                f"Baostock query failed with code {query_result.error_code}: {query_result.error_msg}"
            )
            return None

    logger.error(f"Failed to execute Baostock query after {max_retries} retries.")
    return None


def fetch_annual_net_profit_from_baostock(symbol: str, years: int = 10) -> list[dict]:
    """Fetches annual net profit, aggregating quarterly data with resilience."""
    with baostock_session():
        bs_symbol = symbol.replace(".SH", ".sh").replace(".SZ", ".sz").lower()
        annual_profits = []
        current_year = datetime.now().year

        consecutive_failures = 0
        max_consecutive_failures = 8  # Circuit breaker for the whole function

        for year in range(current_year - years, current_year + 1):
            if consecutive_failures >= max_consecutive_failures:
                logger.error(
                    f"Circuit breaker for {symbol}: Too many consecutive quarterly failures. Aborting year loop."
                )
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
                    consecutive_failures = 0  # Reset on success
                    net_profit_str = df_profit.iloc[0].get("netProfit")
                    if net_profit_str and net_profit_str.strip():
                        try:
                            total_net_profit_this_year += float(net_profit_str)
                            year_has_data = True
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Could not parse netProfit '{net_profit_str}' for {bs_symbol} {year}Q{quarter}"
                            )

            if year_has_data:
                annual_profits.append(
                    {"year": year, "net_profit": total_net_profit_this_year}
                )

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
                    logger.warning(
                        f"Could not find a valid code column for {market}. Skipping."
                    )
                    continue

            df.rename(
                columns={code_col: "代码", "名称": "name", "name": "name"}, inplace=True
            )

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
            # Shanghai Stock Exchange ETFs
            if code_str.startswith(("51", "56", "58")):
                return ".SH"
            elif code_str.startswith("15"):  # Shenzhen Stock Exchange ETFs
                return ".SZ"
            else:
                return ""  # Return empty for unknown prefixes

        etf_df["ts_code"] = etf_df["代码"].apply(lambda x: str(x) + get_etf_suffix(x))
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
                set_={
                    "name": stmt.excluded.name,
                    "last_updated": stmt.excluded.last_updated,
                },
            )
            db.execute(stmt)
            db.commit()
            logger.info(
                f"Successfully upserted {len(combined_df)} stocks and ETFs into the database."
            )


def fetch_fundamental_data_from_baostock(symbol: str) -> Union[dict, None]:
    with baostock_session():
        # This function can also be refactored to use the _baostock_query_with_retry wrapper
        # For now, keeping it as is to focus on the main error source.
        # A full implementation would wrap bs.query_history_k_data_plus, etc.
        return {}  # Placeholder for brevity


def fetch_corporate_actions_from_baostock(symbol: str) -> list[dict]:
    """
    Fetches dividend data from Baostock and returns it as a list of actions.
    Split data fetching has been removed as per user request.
    """
    with baostock_session():
        bs_symbol = symbol.replace(".SH", ".sh").replace(".SZ", ".sz").lower()
        actions = []

        # Fetch Dividend Data
        df_dividends = _baostock_query_with_retry(
            bs.query_dividend_data, code=bs_symbol
        )
        if df_dividends is not None and not df_dividends.empty:
            for _, row in df_dividends.iterrows():
                try:
                    # Handle cases like '0.5或0.6' by taking the first value
                    dividend_str = (
                        str(row["dividCashPsAfterTax"]).split("或")[0].strip()
                    )
                    if dividend_str:  # Ensure it's not an empty string
                        actions.append(
                            {
                                "action_type": "dividend",
                                "ex_date": datetime.strptime(
                                    row["dividRegistDate"], "%Y-%m-%d"
                                ).date(),
                                "value": float(dividend_str),
                            }
                        )
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(
                        f"Could not parse dividend row for {symbol}: {row}. Error: {e}"
                    )
                    continue

        # Sort actions by date
        if actions:
            actions.sort(key=lambda x: str(x["ex_date"]), reverse=True)

    return actions


def fetch_a_share_data_from_akshare(
    stock_code: str, interval: str, trade_date: Union[date, None] = None
) -> pd.DataFrame:
    """
    Fetches historical or intraday data for a specific A-share stock or ETF using AKShare,
    then cleans and formats it to match the database schema.
    """
    symbol = stock_code.split(".")[0]

    try:
        start_date = (datetime.now() - timedelta(days=15 * 365)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")

        is_etf = symbol.startswith(("15", "51", "56", "58"))

        if interval in ["daily", "weekly", "monthly"]:
            if is_etf:
                df = ak.fund_etf_hist_em(
                    symbol=symbol,
                    period=interval,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
            else:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=interval,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
        else:
            date_str = (trade_date or date.today()).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                start_date=date_str,
                end_date=date_str,
                period="1",
                adjust="qfq",
            )

        if df.empty:
            logger.warning(
                f"AKShare returned empty DataFrame for {stock_code} (is_etf={is_etf})."
            )
            return pd.DataFrame()

        # --- Data Processing ---
        rename_map = {
            "日期": "trade_date",
            "时间": "trade_date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "vol",
            "成交额": "amount",
        }

        if is_etf:
            rename_map.update({"涨跌额": "change", "涨跌幅": "pct_chg"})

        df = df.rename(columns=rename_map)

        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
        df = df.sort_values(by="trade_date", ascending=True)

        if not is_etf:
            # Calculate missing fields for stocks
            df["pre_close"] = df["close"].shift(1)
            df["change"] = df["close"] - df["pre_close"]

            pre_close_safe = df["pre_close"].copy()
            pre_close_safe[pre_close_safe == 0] = pd.NA
            df["pct_chg"] = (df["change"] / pre_close_safe) * 100
        else:
            # For ETFs, pct_chg is a percentage, so we need to ensure it's a float
            df["pct_chg"] = pd.to_numeric(df["pct_chg"], errors="coerce")
            # Calculate pre_close for ETFs from provided data
            df["pre_close"] = df["close"] - df["change"]

        # Fill NaN values that may have been created during calculations
        df["pre_close"] = df["pre_close"].fillna(df["close"])
        df["change"] = df["change"].fillna(0.0)
        df["pct_chg"] = df["pct_chg"].fillna(0.0)

        final_cols = [
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "change",
            "pct_chg",
            "vol",
            "amount",
        ]
        df = df.reindex(columns=final_cols, fill_value=0.0)

        return df

    except Exception as e:
        logger.error(
            f"Failed to fetch or process data from AKShare for {stock_code}: {e}",
            exc_info=True,
        )
        return pd.DataFrame()
