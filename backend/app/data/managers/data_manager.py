from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.infrastructure.database import models
from app.infrastructure.database.session import get_db

from ..fetchers.stock_fetchers import a_share_fetcher, us_stock_fetcher
from . import database_writer as db_writer
from .data_utils import calculate_ma

from typing import Union

logger = logging.getLogger(__name__)


def get_all_stocks_list(db: Session, market_type: str = "A_share"):
    """
    Get stock list for a specific market. It serves from a local DB cache.
    If the cache is empty or older than 24 hours for that market, it refreshes from data sources.
    """
    query = db.query(models.StockInfo).filter(
        models.StockInfo.market_type == market_type
    )

    # Simplified logic: if the list is empty, try to refresh it.
    # More complex logic (e.g., checking age) can be added if needed.
    if query.count() == 0:
        try:
            logger.info(
                f"Stock list for {market_type} is empty. Attempting to refresh."
            )
            if market_type == "A_share":
                a_share_fetcher.update_stock_list_from_akshare(db)
            elif market_type == "US_stock":
                us_stock_fetcher.update_us_stock_list(db)
        except Exception as e:
            logger.error(f"Failed to update stock list for {market_type}: {e}")

    return query.all()


def force_update_stock_list(db: Session, market_type: str):
    """
    Explicitly triggers an update of the stock list from the data source.
    """
    logger.info(f"Force updating stock list for {market_type} from source.")
    try:
        if market_type == "A_share":
            a_share_fetcher.update_stock_list_from_akshare(db)
        elif market_type == "US_stock":
            us_stock_fetcher.update_us_stock_list(db)
        logger.info(f"Successfully forced update for {market_type}.")
    except Exception as e:
        logger.error(f"Failed to force update stock list for {market_type}: {e}")
        # Re-raise the exception to be caught by the API endpoint
        raise e


class StockDataFetcher:
    def __init__(
        self,
        db: Session,
        stock_code: str,
        interval: str,
        market_type: str,
        trade_date: Union[date, None] = None,
    ):
        self.db = db
        self.stock_code = stock_code
        self.interval = interval
        self.market_type = market_type
        self.trade_date = trade_date
        self.start_date = (datetime.now() - timedelta(days=15 * 365)).date()
        self.end_date = datetime.now().date()


    def fetch_stock_data(self):
        """
        Main method to fetch stock data, implementing the cache-aside pattern.
        1. Try to fetch from the database.
        2. If not found or incomplete, fetch from the external API.
        3. Store the new data back into the database.
        """
        # For minute/5day intervals, we currently bypass the DB cache and go straight to the source.
        # This logic can be refined to support DB caching for intraday data if needed.
        if self.interval in ["minute", "5day"]:
            df = self._fetch_from_api()
            if not df.empty:
                df = calculate_ma(df)
            return df

        db_data_df = self._fetch_from_db()

        # If we have some data from the DB, check if it's recent enough.
        if not db_data_df.empty:
            last_db_date = pd.to_datetime(db_data_df["trade_date"]).max().date()
            # If the last date in DB is yesterday or today, consider it fresh.
            if last_db_date >= (datetime.now() - timedelta(days=1)).date():
                logger.info(
                    f"DB data for {self.stock_code} is up-to-date. Returning from DB."
                )
                db_data_df = calculate_ma(db_data_df)
                return db_data_df

        logger.info(
            f"DB data for {self.stock_code} is missing or stale. Fetching from API."
        )
        api_data_df = self._fetch_from_api()

        if not api_data_df.empty:
            self._store_in_db(api_data_df)
            api_data_df = calculate_ma(api_data_df)

        return api_data_df


    def _fetch_from_db(self):
        """Fetches stock K-line data from the local SQLite database."""
        logger.info(
            f"Querying DB for {self.stock_code} from {self.start_date} to {self.end_date}"
        )

        query = (
            self.db.query(models.StockData)
            .filter(
                models.StockData.ts_code == self.stock_code,
                models.StockData.interval == self.interval,
                models.StockData.trade_date >= self.start_date,
                models.StockData.trade_date <= self.end_date,
            )
            .order_by(models.StockData.trade_date)
        )

        df = pd.read_sql(query.statement, self.db.connection())
        if not df.empty:
            logger.info(f"Found {len(df)} records in DB for {self.stock_code}.")
            # Drop the 'id' column as it's not needed for the frontend.
            df = df.drop(columns=["id"])
        return df


    def _fetch_from_api(self):
        """Fetches stock data from the appropriate external API based on market type."""
        if self.market_type == "A_share":
            return a_share_fetcher.fetch_a_share_data_from_akshare(
                self.stock_code, self.interval, self.trade_date
            )
        elif self.market_type == "US_stock":
            return us_stock_fetcher.fetch_from_yfinance(
                self.stock_code,
                self.start_date.strftime("%Y-%m-%d"),
                self.end_date.strftime("%Y-%m-%d"),
                self.interval,
            )
        else:
            raise ValueError(f"Unsupported market type: {self.market_type}")


    def _store_in_db(self, df: pd.DataFrame):
        """Stores the fetched DataFrame into the stock_data table."""
        logger.info(
            f"Storing {len(df)} records for {self.stock_code} into the database."
        )
        try:
            db_writer.store_stock_data(self.db, self.stock_code, self.interval, df)
            logger.info("Successfully stored data in DB.")
        except Exception as e:
            logger.error(
                f"Failed to store stock data for {self.stock_code} in DB: {e}",
                exc_info=True,
            )


def fetch_stock_data(
    stock_code: str, interval: str, market_type: str, trade_date: Union[date, None] = None
):
    """
    Main entry point for fetching stock data.
    Instantiates a fetcher and retrieves the data.
    """
    db_gen = get_db()
    db = next(db_gen)
    try:
        fetcher = StockDataFetcher(db, stock_code, interval, market_type, trade_date)
        return fetcher.fetch_stock_data()
    finally:
        next(db_gen, None)


async def sync_financial_data(symbol: str):
    """
    Asynchronous background task to fetch and store financial data.
    """
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        stock_info = (
            db.query(models.StockInfo)
            .filter(models.StockInfo.ts_code == symbol)
            .first()
        )

        market_type = (
            stock_info.market_type
            if stock_info
            else ("US_stock" if "." not in symbol else None)
        )

        if not market_type:
            logger.warning(
                f"Could not determine market type for {symbol}. Aborting sync."
            )
            return

        logger.info(
            f"BACKGROUND_TASK: Dispatching sync for {symbol}, market: {market_type}"
        )
        if market_type == "A_share":
            await _sync_a_share_data(db, symbol)
        elif market_type == "US_stock":
            await _sync_us_stock_data(db, symbol)
    except Exception as e:
        logger.error(f"SYNC_TASK_ERROR for {symbol}: {e}", exc_info=True)
    finally:
        next(db_gen, None)


async def _sync_a_share_data(db: Session, symbol: str):
    """Syncs all financial data for an A-share stock."""
    logger.info(f"BACKGROUND_TASK: Starting data sync for A-share: {symbol}")

    try:
        fund_data = await run_in_threadpool(
            a_share_fetcher.fetch_fundamental_data_from_baostock, symbol
        )
        if fund_data:
            await run_in_threadpool(
                db_writer.store_fundamental_data, db, symbol, fund_data
            )
            logger.info(f"Successfully synced fundamental data for {symbol}.")

        actions_data = await run_in_threadpool(
            a_share_fetcher.fetch_corporate_actions_from_baostock, symbol
        )
        if actions_data:
            count = await run_in_threadpool(
                db_writer.store_corporate_actions, db, symbol, actions_data
            )
            logger.info(f"Successfully synced {count} corporate actions for {symbol}.")

        earnings_data = await run_in_threadpool(
            a_share_fetcher.fetch_annual_net_profit_from_baostock, symbol
        )
        if earnings_data:
            count = await run_in_threadpool(
                db_writer.store_annual_earnings, db, symbol, earnings_data
            )
            logger.info(
                f"Successfully synced {count} annual earnings records for {symbol}."
            )
    except RuntimeError as e:
        logger.error(f"Baostock session error for {symbol}: {e}")
    except Exception as e:
        logger.error(f"Error during A-share data sync for {symbol}: {e}", exc_info=True)


async def _sync_us_stock_data(db: Session, symbol: str):
    """Syncs all financial data for a US stock."""
    logger.info(f"BACKGROUND_TASK: Starting data sync for US stock: {symbol}")

    fund_data = await run_in_threadpool(
        us_stock_fetcher.fetch_us_fundamental_data_from_yfinance, symbol
    )
    if fund_data:
        await run_in_threadpool(db_writer.store_fundamental_data, db, symbol, fund_data)
        logger.info(f"Successfully synced fundamental data for {symbol}.")

    actions_data = await run_in_threadpool(
        us_stock_fetcher.fetch_us_corporate_actions_from_yfinance, symbol
    )
    if actions_data:
        count = await run_in_threadpool(
            db_writer.store_corporate_actions, db, symbol, actions_data
        )
        logger.info(f"Successfully synced {count} corporate actions for {symbol}.")

    earnings_data = await run_in_threadpool(
        us_stock_fetcher.fetch_us_annual_earnings_from_yfinance, symbol
    )
    if earnings_data:
        count = await run_in_threadpool(
            db_writer.store_annual_earnings, db, symbol, earnings_data
        )
        logger.info(
            f"Successfully synced {count} annual earnings records for {symbol}."
        )


def get_fundamental_data_from_db(
    db: Session, symbol: str
) -> Union[models.FundamentalData, None]:
    """
    从数据库中获取指定股票的基本面数据。

    Args:
        db: 数据库会话
        symbol: 股票代码

    Returns:
        基本面数据对象，如果不存在则返回None
    """
    return (
        db.query(models.FundamentalData)
        .filter(models.FundamentalData.symbol == symbol)  # type: ignore[attr-defined]
        .first()
    )


def get_corporate_actions_from_db(
    db: Session, symbol: str
) -> list[models.CorporateAction]:
    """
    从数据库中获取指定股票的公司行为数据。

    Args:
        db: 数据库会话
        symbol: 股票代码

    Returns:
        按除权除息日期排序的公司行为数据列表
    """
    return (
        db.query(models.CorporateAction)
        .filter(models.CorporateAction.symbol == symbol)  # type: ignore[attr-defined]
        .order_by(models.CorporateAction.ex_date)
        .all()
    )


def get_annual_earnings_from_db(
    db: Session, symbol: str
) -> list[models.AnnualEarnings]:
    return (
        db.query(models.AnnualEarnings)
        .filter(models.AnnualEarnings.symbol == symbol)  # type: ignore[attr-defined]
        .order_by(models.AnnualEarnings.year)  # type: ignore[attr-defined]
        .all()
    )


def resolve_symbol(db: Session, symbol: str) -> Union[str, None]:
    """
    Resolves a potentially incomplete stock symbol to its full ts_code.
    """
    if "." in symbol:
        return symbol

    a_share_info = (
        db.query(models.StockInfo)
        .filter(
            models.StockInfo.market_type == "A_share",
            models.StockInfo.ts_code.ilike(f"{symbol}.%"),  # type: ignore[attr-defined]
        )
        .first()
    )
    if a_share_info:
        return str(a_share_info.ts_code)

    us_stock_info = (
        db.query(models.StockInfo)
        .filter(
            models.StockInfo.market_type == "US_stock",
            models.StockInfo.ts_code.ilike(symbol),  # type: ignore[attr-defined]
        )
        .first()
    )
    if us_stock_info:
        return str(us_stock_info.ts_code)

    if not any(char.isdigit() for char in symbol):
        return symbol.upper()

    logger.warning(f"Could not resolve symbol: {symbol}")
    return None
