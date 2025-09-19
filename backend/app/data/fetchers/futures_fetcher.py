from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Literal, Union

import akshare as ak
import numpy as np
import pandas as pd
import yfinance as yf

from ..managers.data_utils import calculate_ma

logger = logging.getLogger(__name__)


def fetch_futures_from_yfinance(
    symbol: str, start_date: str, end_date: str, interval: str = "daily"
) -> pd.DataFrame:
    """
    Fetches futures data from yfinance and formats it.
    """
    logger.info(
        f"Fetching yfinance data for futures symbol: {symbol}, interval: {interval}, start: {start_date}, end: {end_date}"
    )

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    interval_map = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}
    yf_interval = interval_map.get(interval, "1d")

    df = yf.download(
        symbol,
        start=start_dt,
        end=end_dt,
        interval=yf_interval,
        auto_adjust=False,
        progress=False,
    )

    if df is None or df.empty:
        logger.warning(f"yfinance returned empty DataFrame for {symbol}")
        return pd.DataFrame()

    df.reset_index(inplace=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(subset=["Date"], inplace=True)
    if df is None or df.empty:
        logger.warning(
            f"DataFrame became empty after dropping rows with missing dates for {symbol}"
        )
        return pd.DataFrame()

    df.rename(
        columns={
            "Date": "trade_date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "vol",
        },
        inplace=True,
    )

    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")

    numeric_cols = ["open", "high", "low", "close", "vol"]
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if col == "vol":
                df[col] = df[col].fillna(0.0).astype(float)

    df.sort_values(by="trade_date", inplace=True)
    df["pre_close"] = df["close"].shift(1)
    df["pre_close"] = df["pre_close"].fillna(df["open"])

    df["change"] = df["close"] - df["pre_close"]
    df["pct_chg"] = (df["change"] / df["pre_close"].replace(0, pd.NA)) * 100
    df["pct_chg"] = pd.to_numeric(df["pct_chg"], errors="coerce").fillna(0.0)

    if "amount" not in df.columns:
        df["amount"] = df["close"] * df["vol"]

    # ** THE FIX: Replace 0s with NaN in price columns before MA calculation **
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        if col in df.columns:
            df[col] = df[col].replace(0, np.nan)

    df = calculate_ma(df)

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
        "ma5",
        "ma10",
        "ma20",
        "ma60",
    ]

    for col in final_cols:
        if col not in df.columns:
            df[col] = None

    result = df[final_cols]

    # Ensure we return a DataFrame, not a Series
    if isinstance(result, pd.Series):
        result = result.to_frame().T

    return result


def _is_china_futures_contract(symbol: str) -> bool:
    """Return True if symbol looks like a China futures contract or main-continuous code.

    Matches examples:
    - rb2410, TA2409 (letters + 4 digits)
    - rb240, AG309 (letters + 3 digits)
    - V0, RB0 (letters + '0' main-continuous)
    """
    return re.fullmatch(r"[A-Za-z]{1,3}(?:[0-9]{3,4}|0)", symbol) is not None


def _standardize_akshare_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename various possible Akshare column names to standard names used by our schemas."""
    column_map_variants = [
        {
            "date": "trade_date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "vol",
        },
        {
            "日期": "trade_date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "vol",
        },
    ]
    for mapping in column_map_variants:
        intersect = set(mapping.keys()) & set(df.columns)
        if intersect:
            df = df.rename(columns=mapping)
            break
    return df


def _aggregate_interval(
    df: pd.DataFrame, interval: Literal["daily", "weekly", "monthly"]
) -> pd.DataFrame:
    if interval == "daily":
        return df
    # Ensure datetime index
    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    rule = "W-FRI" if interval == "weekly" else "M"
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "vol": "sum",
        "amount": "sum",
    }
    df_agg = df.resample(rule).agg(agg).dropna(how="any")
    df_agg = df_agg.reset_index().rename(columns={"trade_date": "trade_date"})
    df_agg["trade_date"] = df_agg["trade_date"].dt.strftime("%Y-%m-%d")
    return df_agg


def fetch_china_futures_from_akshare(
    symbol: str,
    start_date: str,
    end_date: str,
    interval: Literal["daily", "weekly", "monthly"] = "daily",
) -> pd.DataFrame:
    """
    Fetch China futures contract OHLCV via Akshare and format to standard schema.
    Supports interval aggregation to weekly/monthly.
    """
    upper_symbol = symbol.upper()
    logger.info(
        f"Fetching Akshare data for China futures symbol: {upper_symbol}, interval: {interval}, start: {start_date}, end: {end_date}"
    )

    candidates: list[str] = []
    if upper_symbol.endswith("0") and len(upper_symbol) >= 2:
        # Main-continuous like RB0/V0 -> try recent and near-future delivery months
        base = upper_symbol[:-1]
        try:
            start_ts = pd.to_datetime(start_date)
            end_ts = pd.to_datetime(end_date)
        except Exception:
            start_ts = pd.Timestamp.today() - pd.Timedelta(days=365)
            end_ts = pd.Timestamp.today()
        # Handle potential NaT values
        if start_ts is pd.NaT or (
            hasattr(start_ts, "__array__") and start_ts.isna().any()
        ):
            start_ts = pd.Timestamp.today() - pd.Timedelta(days=365)
        if end_ts is pd.NaT or (hasattr(end_ts, "__array__") and end_ts.isna().any()):
            end_ts = pd.Timestamp.today()

        # Ensure timestamps are valid before arithmetic operations
        if isinstance(start_ts, pd.Timestamp) and start_ts is not pd.NaT:
            range_start = start_ts - pd.offsets.MonthBegin(1)
        else:
            range_start = (
                pd.Timestamp.today() - pd.Timedelta(days=365) - pd.offsets.MonthBegin(1)
            )

        if isinstance(end_ts, pd.Timestamp) and end_ts is not pd.NaT:
            range_end = end_ts + pd.offsets.MonthBegin(3)
        else:
            range_end = pd.Timestamp.today() + pd.offsets.MonthBegin(3)

        month_range = pd.date_range(
            range_start,
            range_end,
            freq="MS",
        )
        ym_codes = list(dict.fromkeys([dt.strftime("%y%m") for dt in month_range]))
        candidates = [
            f"{base}{ym}" for ym in ym_codes[::-1]
        ]  # try nearest months first
    else:
        candidates = [upper_symbol]

    df = pd.DataFrame()
    last_exc: Union[Exception, None] = None
    for cand in candidates:
        try:
            logger.info(f"Trying Akshare contract: {cand}")
            tmp = ak.futures_zh_daily_sina(symbol=cand)
            if tmp is not None and not tmp.empty:
                df = tmp
                upper_symbol = cand
                break
        except Exception as exc:
            last_exc = exc
            continue

    if df is None or df.empty:
        if last_exc:
            logger.error(
                f"Akshare returned empty for {upper_symbol}; last error: {last_exc}"
            )
        else:
            logger.warning(f"Akshare returned empty DataFrame for {upper_symbol}")
        return pd.DataFrame()

    df = _standardize_akshare_columns(df)

    if "trade_date" not in df.columns:
        logger.error(f"Akshare data missing 'trade_date' for {upper_symbol}")
        return pd.DataFrame()

    # Normalize types
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    for col in ["open", "high", "low", "close", "vol"]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Filter date range
    mask = (df["trade_date"] >= start_date) & (df["trade_date"] <= end_date)
    df = df.loc[mask].copy()
    if df is None or df.empty:
        return pd.DataFrame()

    # Ensure amount
    if "amount" not in df.columns:
        df["amount"] = df["close"] * df["vol"]

    # Replace 0 price with NaN for MA calc
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].replace(0, np.nan)

    # Compute MAs and changes
    df.sort_values(by="trade_date", inplace=True)
    df = calculate_ma(df)
    df["pre_close"] = df["close"].shift(1)
    df["pre_close"] = df["pre_close"].fillna(df["open"])
    df["change"] = df["close"] - df["pre_close"]
    df["pct_chg"] = (df["change"] / df["pre_close"].replace(0, pd.NA)) * 100
    df["pct_chg"] = pd.to_numeric(df["pct_chg"], errors="coerce").fillna(0.0)

    # Aggregate if needed
    df = _aggregate_interval(df, interval)

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
        "ma5",
        "ma10",
        "ma20",
        "ma60",
    ]
    for col in final_cols:
        if col not in df.columns:
            df[col] = None
    result = df[final_cols]

    # Ensure we return a DataFrame, not a Series
    if isinstance(result, pd.Series):
        result = result.to_frame().T

    return result
