from __future__ import annotations

import logging
from datetime import datetime

# 新增：为静态类型检查引入 cast
from typing import Any, cast

import pandas as pd

# 新增：用于 Wikipedia 回退抓取
import yahoo_fin.stock_info as si
import yfinance as yf

# 新增：按方言引入 PostgreSQL insert（最小范围引入，不影响 SQLite）
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.infrastructure.database import models

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

    if df is None or df.empty:
        logger.warning(f"yfinance returned empty or None DataFrame for {yf_ticker}")
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
    if hasattr(df, "columns") and isinstance(df.columns, pd.MultiIndex):
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

    # Ensure we return a DataFrame, not a Series
    if isinstance(df, pd.Series):
        df = df.to_frame().T

    logger.info(f"Final DataFrame columns for {yf_ticker}: {df.columns.tolist()}")
    logger.debug(
        f"First 5 rows of final DataFrame for {yf_ticker}:\n{df.head().to_string()}"
    )

    return df


# 新增：Alpha Vantage API 抓取 S&P 500 列表，作为主要数据源
def _fetch_sp500_from_alphavantage() -> list[str]:
    """使用 Alpha Vantage API 获取 S&P 500 成分股列表"""
    try:
        from app.core.config import settings

        if (
            not settings.ALPHAVANTAGE_API_KEY
            or settings.ALPHAVANTAGE_API_KEY == "YOUR_KEY_HERE"
        ):
            logger.warning(
                "Alpha Vantage API key not configured, falling back to yfinance"
            )
            return []

        import requests

        url = "https://www.alphavantage.co/query"
        params = {"function": "LISTING_STATUS", "apikey": settings.ALPHAVANTAGE_API_KEY}

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()

        # 检查响应内容是否为空
        if not resp.text.strip():
            logger.warning("Alpha Vantage API returned empty response")
            return []

        # 记录响应内容的前200个字符用于调试
        logger.debug(f"Alpha Vantage API response: {resp.text[:200]}...")

        # Alpha Vantage LISTING_STATUS API 返回 CSV 格式数据
        # 解析 CSV 数据
        symbols = []
        lines = resp.text.strip().split("\n")

        if len(lines) <= 1:  # 只有表头或空数据
            logger.warning("Alpha Vantage API returned no data or only headers")
            return []

        # 跳过表头行，处理数据行
        for line in lines[1:]:
            try:
                fields = line.strip().split(",")
                if len(fields) >= 7:  # 确保有足够的字段
                    symbol = fields[0].strip('"')
                    exchange = fields[2].strip('"')
                    asset_type = fields[3].strip('"')
                    status = fields[6].strip('"')

                    # 只选择活跃的股票类型，在主要交易所
                    if (
                        asset_type == "Stock"
                        and exchange in ["NYSE", "NASDAQ", "NYSE ARCA"]
                        and status == "Active"
                        and symbol
                    ):
                        symbols.append(symbol)

            except Exception as line_error:
                logger.warning(f"Failed to parse line: {line}, error: {line_error}")
                continue

        if symbols:
            logger.info(f"Alpha Vantage fetched {len(symbols)} US stock tickers.")
            return symbols
        else:
            logger.warning("Alpha Vantage returned empty or invalid data")
            return []

    except Exception as e:
        logger.error(f"Alpha Vantage API for S&P 500 failed: {e}", exc_info=True)
        return []


# 新增：使用 yfinance 获取股票列表作为备用方案


def _fetch_us_stocks_from_yfinance() -> list[str]:
    """使用 yfinance 获取美股列表"""
    try:
        # 获取主要交易所的股票
        symbols = set()

        # 方法1: 尝试获取主要指数成分股（yfinance 不支持此功能）
        # yfinance 库设计用于获取单个股票数据，不提供指数成分股列表
        # 此功能会失败，直接进入方法2

        # 方法2: 使用更全面的主要股票列表
        logger.info("Using comprehensive US stock list as yfinance fallback")

        # 扩展的主要美股代码列表（约100个主要股票）
        major_stocks = [
            # 科技股
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "META",
            "TSLA",
            "NVDA",
            "ADBE",
            "CRM",
            "ORCL",
            "INTC",
            "CSCO",
            "IBM",
            "QCOM",
            "TXN",
            "AMD",
            "NOW",
            "SNOW",
            "NET",
            "ZS",
            "PANW",
            "CRWD",
            "OKTA",
            "TEAM",
            "DOCU",
            "TWLO",
            "SQ",
            "PYPL",
            "SHOP",
            "MDB",
            # 金融股
            "JPM",
            "BAC",
            "WFC",
            "C",
            "GS",
            "MS",
            "AXP",
            "V",
            "MA",
            "PYPL",
            "SPGI",
            "MCO",
            "BLK",
            "SCHW",
            "ICE",
            "CME",
            "NDAQ",
            "FIS",
            "FISV",
            "GPN",
            # 医疗保健股
            "JNJ",
            "PFE",
            "MRK",
            "ABT",
            "TMO",
            "DHR",
            "LLY",
            "AMGN",
            "GILD",
            "REGN",
            "VRTX",
            "BIIB",
            "ISRG",
            "SYK",
            "BDX",
            "EW",
            "ZTS",
            "HCA",
            "CVS",
            "CI",
            # 消费股
            "PG",
            "KO",
            "PEP",
            "WMT",
            "COST",
            "TGT",
            "HD",
            "LOW",
            "NKE",
            "SBUX",
            "MCD",
            "YUM",
            "EL",
            "CL",
            "KMB",
            "K",
            "GIS",
            "HSY",
            "SYY",
            "KR",
            # 工业股
            "UNP",
            "UPS",
            "FDX",
            "CAT",
            "DE",
            "HON",
            "GE",
            "MMM",
            "BA",
            "LMT",
            "RTX",
            "NOC",
            "GD",
            "EMR",
            "ITW",
            "ETN",
            "ROP",
            "FAST",
            "GWW",
            "PH",
            # 能源和材料
            "XOM",
            "CVX",
            "COP",
            "EOG",
            "SLB",
            "HAL",
            "APD",
            "LIN",
            "ECL",
            "DD",
            "DOW",
            "NEM",
            "FCX",
            "VALE",
            "RIO",
            "BHP",
            "SCCO",
            "AA",
            "STLD",
            "NUE",
        ]
        symbols.update(major_stocks)

        if symbols:
            logger.info(f"yfinance fallback fetched {len(symbols)} US stock tickers.")
            return list(symbols)
        else:
            logger.warning("yfinance returned empty stock list")
            return []

    except Exception as e:
        logger.error(f"yfinance stock list fetch failed: {e}", exc_info=True)
        return []


def update_us_stock_list(db: Session):
    """
    Fetches a comprehensive list of US stock symbols from various exchanges
    using yahoo_fin and upserts it into the stock_info table.
    """
    all_symbols: set[str] = set()

    # Fetch sources independently so one failure doesn't abort the entire update
    def _safe_fetch(name: str, fetcher) -> list[str]:
        try:
            logger.info(f"Fetching {name} tickers...")
            tickers = fetcher()
            logger.info(f"Fetched {len(tickers)} {name} tickers.")
            return tickers or []
        except Exception as e:
            logger.error(f"Error fetching {name} tickers: {e}", exc_info=True)
            return []

    # IMPORTANT: For S&P 500, if it raises exception, STOP immediately (match tests)
    try:
        logger.info("Fetching S&P 500 tickers...")
        sp500_tickers = si.tickers_sp500()
        logger.info(f"Fetched {len(sp500_tickers)} S&P 500 tickers.")
    except Exception as e:
        logger.error(f"Error fetching S&P 500 tickers: {e}", exc_info=True)
        return

    # 标准化类型，避免 DataFrame/其他可迭代引发的布尔判断与类型问题
    if isinstance(sp500_tickers, pd.DataFrame):
        sp500_tickers = []
    elif not isinstance(sp500_tickers, list):
        try:
            sp500_tickers = list(sp500_tickers)  # type: ignore[arg-type]
        except Exception:
            sp500_tickers = []

    if not sp500_tickers:
        # 当 yahoo_fin 抓取为空时，可使用 Alpha Vantage 回退
        alpha_sp500 = _safe_fetch(
            "S&P 500 (Alpha Vantage fallback)", _fetch_sp500_from_alphavantage
        )
        sp500_tickers = alpha_sp500

    all_symbols.update(sp500_tickers)

    nasdaq_tickers = _safe_fetch("NASDAQ", si.tickers_nasdaq)
    all_symbols.update(nasdaq_tickers)

    dow_tickers = _safe_fetch("Dow Jones", si.tickers_dow)
    all_symbols.update(dow_tickers)

    other_tickers = _safe_fetch("other US (NYSE/AMEX/etc.)", si.tickers_other)
    all_symbols.update(other_tickers)

    # 仅当完全没有获取到任何 ticker 时，才使用 yfinance 的回退列表
    if len(all_symbols) == 0:
        logger.warning("No stocks fetched from yahoo_fin, using yfinance fallback")
        yfinance_tickers = _safe_fetch(
            "yfinance fallback", _fetch_us_stocks_from_yfinance
        )
        all_symbols.update(yfinance_tickers)

    logger.info(f"Total unique symbols fetched from yahoo_fin: {len(all_symbols)}")

    # Fallback: if all sources failed or returned empty, seed with a minimal set
    if not all_symbols:
        logger.warning(
            "No US tickers fetched from yahoo_fin sources. Seeding a minimal fallback set to avoid empty list."
        )
        all_symbols.update({"AAPL", "MSFT", "GOOG", "AMZN", "TSLA"})

    # Optional: Filter out symbols with certain suffixes (e.g., warrants, rights issues)
    del_suffixes = ["W", "R", "P", "Q"]
    qualified_symbols: set[str] = set()
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
        # 按数据库方言选择 upsert 实现，避免 OnConflictDoUpdate 方言不匹配
        if db.bind is not None and db.bind.dialect.name == "sqlite":
            stmt = sqlite_insert(models.StockInfo).values(stocks_to_insert)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ts_code", "market_type"],
                set_={
                    "name": stmt.excluded.name,
                    "last_updated": stmt.excluded.last_updated,
                },
            )
        else:
            stmt = pg_insert(models.StockInfo).values(stocks_to_insert)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ts_code", "market_type"],
                set_={
                    "name": stmt.excluded.name,
                    "last_updated": stmt.excluded.last_updated,
                },
            )
        try:
            db.execute(stmt)
            db.commit()
            logger.info(
                f"Successfully upserted {len(stocks_to_insert)} US stock entries into DB."
            )

            # 更新股票名称（包括中文名称）
            update_stock_names_from_yfinance(db)

        except Exception as e:
            logger.error(f"Error upserting US stock entries to DB: {e}", exc_info=True)
            db.rollback()
    else:
        logger.warning("No US stock symbols available to update after filtering.")


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
            "dividend_yield": (
                info.get("dividendYield", 0) * 100
                if info.get("dividendYield")
                else None
            ),
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
            for idx, value in dividends.items():
                # 使用 typing.cast 明确告诉类型检查器 idx 可转换为时间戳
                ex_dt = pd.Timestamp(cast("Any", idx)).date()
                actions_list.append(
                    {"action_type": "dividend", "ex_date": ex_dt, "value": value}
                )

        splits = ticker.splits
        if not splits.empty:
            for idx, value in splits.items():
                ex_dt = pd.Timestamp(cast("Any", idx)).date()
                actions_list.append(
                    {"action_type": "split", "ex_date": ex_dt, "value": value}
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
            for idx, value in annual_net_income.items():
                if not pd.isna(value).any():
                    year_val = pd.Timestamp(cast("Any", idx)).year
                    earnings_list.append({"year": year_val, "net_profit": value})
        return earnings_list
    except Exception as e:
        logger.error(f"yfinance: Failed to fetch annual earnings for {symbol}: {e}")
        return []


def update_stock_names_from_yfinance(db: Session):
    """
    使用 yfinance 更新股票名称（包括中文名称）

    从数据库中获取所有美股代码，使用 yfinance 获取详细的股票信息，
    包括中文名称（longName/shortName），并更新到数据库。
    """
    try:
        logger.info("Starting to update US stock names from yfinance...")

        # 获取所有美股代码
        us_stocks = (
            db.query(models.StockInfo)
            .filter(models.StockInfo.market_type == "US_stock")  # type: ignore
            .all()
        )

        if not us_stocks:
            logger.warning("No US stocks found in database to update names")
            return

        logger.info(f"Found {len(us_stocks)} US stocks to update names")

        updated_count = 0

        for stock in us_stocks:
            try:
                # 使用 yfinance 获取股票信息
                ticker = yf.Ticker(stock.ts_code)
                info = ticker.info

                if not info:
                    logger.debug(f"No yfinance info found for {stock.ts_code}")
                    continue

                # 优先使用 longName（完整名称），如果没有则使用 shortName
                stock_name = info.get("longName") or info.get("shortName")

                if stock_name and stock_name != stock.name:
                    # 更新股票名称
                    stock.name = stock_name
                    updated_count += 1
                    logger.debug(f"Updated {stock.ts_code} name: {stock.name}")

            except Exception as e:
                logger.warning(f"Failed to update name for {stock.ts_code}: {e}")
                continue

        # 提交更改到数据库
        db.commit()
        logger.info(
            f"Successfully updated {updated_count} US stock names from yfinance"
        )

    except Exception as e:
        logger.error(f"Error updating US stock names from yfinance: {e}", exc_info=True)
        db.rollback()
