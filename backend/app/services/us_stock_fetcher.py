import yfinance as yf
import pandas as pd
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.db import models
import yahoo_fin.stock_info as si

logger = logging.getLogger(__name__)


def _convert_ts_code_to_yfinance(ts_code):
    """Converts Tushare code to yfinance ticker format."""
    if ts_code.endswith(".SH"):
        return ts_code.replace(".SH", ".SS")
    return ts_code


def fetch_from_yfinance(
    ts_code: str, start_date: str, end_date: str, interval: str = "1d"
) -> pd.DataFrame:
    """
    Fetches data from yfinance and formats it to match Tushare's output.
    """
    yf_ticker = _convert_ts_code_to_yfinance(ts_code)
    logger.info(
        f"Fetching yfinance data for ticker: {yf_ticker}, interval: {interval}, start: {start_date}, end: {end_date}"
    )

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    interval_map = {
        "daily": "1d",
        "weekly": "1wk",
        "monthly": "1mo",
    }
    yf_interval = interval_map.get(interval, "1d")

    # Use yfinance to download data
    df = yf.download(
        yf_ticker,
        start=start_dt,
        end=end_dt,
        interval=yf_interval,
        auto_adjust=False,
        progress=False,
    )

    if df.empty:
        logger.warning(f"yfinance returned empty DataFrame for {yf_ticker}")
        return pd.DataFrame()

    logger.info(
        f"Successfully fetched {len(df)} rows from yfinance for {yf_ticker}. Original Columns: {df.columns.tolist()}"
    )
    logger.debug(
        f"First 5 rows of original yfinance data for {yf_ticker}:\n{df.head().to_string()}"
    )

    # The 'Date' is in the index, reset it to be a column
    df.reset_index(inplace=True)

    # Handle MultiIndex columns that yfinance might return, especially when fetching single tickers
    # by taking the first level of the column index.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Drop rows where 'Date' is NaN/NaT after it has been reset from the index
    df.dropna(subset=["Date"], inplace=True)
    if df.empty:
        logger.warning(
            f"DataFrame became empty after dropping rows with missing dates for {yf_ticker}"
        )
        return pd.DataFrame()

    # Rename columns to match the format used in the rest of the application
    df.rename(
        columns={
            "Date": "trade_date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "vol",
            "Adj Close": "adj_close",
        },
        inplace=True,
    )

    # Convert trade_date to string format YYYY-MM-DD
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")

    # Ensure essential numeric columns exist and are float type, fill NaN with 0.0
    numeric_cols = [
        "open",
        "high",
        "low",
        "close",
        "vol",
        "pre_close",
        "change",
        "pct_chg",
    ]
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Calculate pre_close, change, and pct_chg
    df.sort_values(by="trade_date", inplace=True)
    df["pre_close"] = df["close"].shift(1)
    # For the first row, pre_close can be the same as close
    df["pre_close"] = df["pre_close"].fillna(df["close"])

    df["change"] = df["close"] - df["pre_close"]
    # Avoid division by zero
    df["pct_chg"] = (df["change"] / df["pre_close"].replace(0, pd.NA)) * 100
    df["pct_chg"] = df["pct_chg"].fillna(0.0)

    # yfinance doesn't provide 'amount'. Calculate it as a proxy.
    if "amount" not in df.columns:
        df["amount"] = df["close"] * df["vol"]

    # Select and reorder columns to match the desired schema
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
    # Make sure all final columns are present
    for col in final_cols:
        if col not in df.columns:
            df[col] = 0.0

    df = df[final_cols]

    logger.info(f"Final DataFrame columns for {yf_ticker}: {df.columns.tolist()}")
    logger.debug(
        f"First 5 rows of final DataFrame for {yf_ticker}:\n{df.head().to_string()}"
    )

    return df


def update_us_stock_list(db: Session):
    """
    Fetches a comprehensive list of US stock symbols from various exchanges
    using yahoo_fin and upserts it into the stock_info table.
    """
    all_symbols = set()
    try:
        logger.info("Fetching S&P 500 tickers...")
        sp500_tickers = si.tickers_sp500()
        logger.info(f"Fetched {len(sp500_tickers)} S&P 500 tickers.")
        all_symbols.update(sp500_tickers)

        logger.info("Fetching NASDAQ tickers...")
        nasdaq_tickers = si.tickers_nasdaq()
        logger.info(f"Fetched {len(nasdaq_tickers)} NASDAQ tickers.")
        all_symbols.update(nasdaq_tickers)

        logger.info("Fetching Dow Jones tickers...")
        dow_tickers = si.tickers_dow()
        logger.info(f"Fetched {len(dow_tickers)} Dow Jones tickers.")
        all_symbols.update(dow_tickers)

        logger.info("Fetching 'other' US tickers (NYSE, AMEX, etc.)...")
        other_tickers = si.tickers_other()
        logger.info(f"Fetched {len(other_tickers)} 'other' US tickers.")
        all_symbols.update(other_tickers)

        logger.info(f"Total unique symbols fetched from yahoo_fin: {len(all_symbols)}")

    except Exception as e:
        logger.error(
            f"Error fetching US stock symbols with yahoo_fin: {e}", exc_info=True
        )
        return

    # Optional: Filter out symbols with certain suffixes (e.g., warrants, rights issues)
    del_suffixes = ["W", "R", "P", "Q"]
    qualified_symbols = set()
    for symbol in all_symbols:
        if len(symbol) > 4 and symbol[-1] in del_suffixes:
            continue
        else:
            qualified_symbols.add(symbol)

    logger.info(f"Total qualified symbols after filtering: {len(qualified_symbols)}")

    stocks_to_insert = []
    for symbol in qualified_symbols:
        stocks_to_insert.append(
            {
                "ts_code": symbol,
                "name": symbol,  # Name will be updated later if available via yfinance info
                "market_type": "US_stock",
                "last_updated": datetime.utcnow(),
            }
        )

    if stocks_to_insert:
        stmt = sqlite_insert(models.StockInfo).values(stocks_to_insert)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ts_code", "market_type"],
            set_=dict(name=stmt.excluded.name, last_updated=stmt.excluded.last_updated),
        )
        try:
            db.execute(stmt)
            db.commit()
            logger.info(
                f"Successfully upserted {len(stocks_to_insert)} US stock entries into DB."
            )
        except Exception as e:
            logger.error(f"Error upserting US stock entries to DB: {e}", exc_info=True)
            db.rollback()
    else:
        logger.warning("No US stock symbols fetched to update.")


def fetch_us_fundamental_data_from_yfinance(symbol: str) -> dict | None:
    """Fetches fundamental data for a US stock from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info:
            logger.warning(f"yfinance: No data found for {symbol}")
            return None

        data = {
            "symbol": symbol,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield", 0) * 100
            if info.get("dividendYield")
            else None,
            "eps": info.get("trailingEps"),
            "beta": info.get("beta"),
            "gross_profit_margin": info.get("grossMargins"),
            "net_profit_margin": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
            "revenue_growth_rate": info.get("revenueGrowth"),
            "net_profit_growth_rate": None,
            "debt_to_asset_ratio": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
        }
        return data
    except Exception as e:
        logger.error(f"yfinance: Failed to fetch fundamental data for {symbol}: {e}")
        return None


def fetch_us_corporate_actions_from_yfinance(symbol: str) -> list[dict]:
    """Fetches corporate actions (dividends and splits) for a US stock from yfinance."""
    actions_list = []
    try:
        ticker = yf.Ticker(symbol)

        dividends = ticker.dividends
        if not dividends.empty:
            for date, value in dividends.items():
                actions_list.append(
                    {"action_type": "dividend", "ex_date": date.date(), "value": value}
                )

        splits = ticker.splits
        if not splits.empty:
            for date, value in splits.items():
                actions_list.append(
                    {"action_type": "split", "ex_date": date.date(), "value": value}
                )
        return actions_list
    except Exception as e:
        logger.error(f"yfinance: Failed to fetch corporate actions for {symbol}: {e}")
        return []


def fetch_us_annual_earnings_from_yfinance(symbol: str) -> list[dict]:
    """Fetches annual earnings (net income) for a US stock from yfinance."""
    earnings_list = []
    try:
        ticker = yf.Ticker(symbol)
        financials = ticker.financials
        if not financials.empty and "Net Income" in financials.index:
            annual_net_income = financials.loc["Net Income"]
            for date, value in annual_net_income.items():
                if pd.notna(value):
                    earnings_list.append({"year": date.year, "net_profit": value})
        return earnings_list
    except Exception as e:
        logger.error(f"yfinance: Failed to fetch annual earnings for {symbol}: {e}")
        return []
