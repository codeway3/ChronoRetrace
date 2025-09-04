import logging
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

from .data_utils import calculate_ma

logger = logging.getLogger(__name__)


def get_expiration_dates(symbol: str) -> tuple:
    """
    Fetches the available expiration dates for a given underlying stock symbol.
    """
    logger.info(f"Fetching expiration dates for underlying symbol: {symbol}")
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            logger.warning(f"No expiration dates found for symbol: {symbol}")
        return expirations
    except Exception as e:
        logger.error(
            f"Failed to fetch expiration dates for {symbol}: {e}", exc_info=True
        )
        raise


def get_option_chain(symbol: str, expiration_date: str):
    """
    Fetches the option chain (both calls and puts) for a given symbol and expiration date.
    """
    logger.info(f"Fetching option chain for {symbol} on {expiration_date}")
    try:
        ticker = yf.Ticker(symbol)
        option_chain = ticker.option_chain(expiration_date)

        calls = option_chain.calls
        puts = option_chain.puts

        # Add a 'type' column
        calls["type"] = "call"
        puts["type"] = "put"

        # Combine and select relevant columns
        combined = pd.concat([calls, puts])

        # Rename columns for consistency
        combined.rename(
            columns={
                "contractSymbol": "contract_symbol",
                "lastTradeDate": "last_trade_date",
                "strike": "strike",
                "lastPrice": "last_price",
                "bid": "bid",
                "ask": "ask",
                "change": "change",
                "percentChange": "percent_change",
                "volume": "volume",
                "openInterest": "open_interest",
                "impliedVolatility": "implied_volatility",
                "inTheMoney": "in_the_money",
                "contractSize": "contract_size",
                "currency": "currency",
            },
            inplace=True,
        )

        # Convert timestamp columns to string
        for col in ["last_trade_date"]:
            if col in combined.columns:
                combined[col] = pd.to_datetime(combined[col]).dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        # Fill NaN values with something more JSON-friendly (e.g., None or 0)
        combined.fillna(0, inplace=True)

        return combined.to_dict("records")

    except Exception as e:
        logger.error(
            f"Failed to fetch option chain for {symbol} on {expiration_date}: {e}",
            exc_info=True,
        )
        raise


def fetch_options_from_yfinance(
    symbol: str, start_date: str, end_date: str, interval: str = "1d"
) -> pd.DataFrame:
    """
    Fetches historical options data from yfinance and formats it.
    """
    logger.info(
        f"Fetching yfinance data for options symbol: {symbol}, interval: {interval}, start: {start_date}, end: {end_date}"
    )

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    interval_map = {
        "daily": "1d",
        "weekly": "1wk",
        "monthly": "1mo",
    }
    yf_interval = interval_map.get(interval, "1d")

    df = yf.download(
        symbol,
        start=start_dt,
        end=end_dt,
        interval=yf_interval,
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        logger.warning(f"yfinance returned empty DataFrame for {symbol}")
        return pd.DataFrame()

    df.reset_index(inplace=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(subset=["Date"], inplace=True)
    if df.empty:
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

    return df[final_cols]
