import logging
from typing import Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.db import models
from app.db.session import get_db
from . import a_share_fetcher, us_stock_fetcher, db_writer

logger = logging.getLogger(__name__)


def get_all_stocks_list(db: Session, market_type: str = "A_share"):
    """
    Get stock list for a specific market. It serves from a local DB cache.
    If the cache is empty or older than 24 hours for that market, it refreshes from data sources.
    """
    query = db.query(models.StockInfo).filter(models.StockInfo.market_type == market_type)
    stock_count = query.count()
    first_record = query.first()

    refresh_needed = stock_count == 0 or \
                     (first_record and (datetime.utcnow() - first_record.last_updated) > timedelta(hours=24))

    if refresh_needed:
        try:
            if market_type == "A_share":
                logger.info("Refreshing A-share stock list...")
                a_share_fetcher.update_stock_list_from_akshare(db)
            elif market_type == "US_stock":
                logger.info("Refreshing US stock list...")
                us_stock_fetcher.update_us_stock_list(db)
        except Exception as e:
            logger.error(f"Failed to update stock list for {market_type}: {e}")

    return query.all()


def fetch_stock_data(stock_code: str, interval: str, market_type: str, trade_date: Optional[date] = None):
    """
    Fetches historical or intraday data for a specific stock.
    """
    if market_type == "A_share":
        return a_share_fetcher.fetch_a_share_data_from_akshare(stock_code, interval, trade_date)
    elif market_type == "US_stock":
        yf_interval_map = {
            "minute": "1d", "5day": "1d", "daily": "1d",
            "weekly": "1wk", "monthly": "1mo",
        }
        yf_interval = yf_interval_map.get(interval, "1d")
        start_date = (datetime.now() - timedelta(days=15 * 365)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        return us_stock_fetcher.fetch_from_yfinance(stock_code, start_date, end_date, yf_interval)
    else:
        raise ValueError(f"Unsupported market type: {market_type}")


async def sync_financial_data(symbol: str):
    """
    Asynchronous background task to fetch and store financial data.
    """
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        stock_info = db.query(models.StockInfo).filter(models.StockInfo.ts_code == symbol).first()
        
        market_type = stock_info.market_type if stock_info else ('US_stock' if '.' not in symbol else None)

        if not market_type:
            logger.warning(f"Could not determine market type for {symbol}. Aborting sync.")
            return

        logger.info(f"BACKGROUND_TASK: Dispatching sync for {symbol}, market: {market_type}")
        if market_type == 'A_share':
            await _sync_a_share_data(db, symbol)
        elif market_type == 'US_stock':
            await _sync_us_stock_data(db, symbol)
    except Exception as e:
        logger.error(f"SYNC_TASK_ERROR for {symbol}: {e}", exc_info=True)
    finally:
        next(db_gen, None)


async def _sync_a_share_data(db: Session, symbol: str):
    """Syncs all financial data for an A-share stock."""
    logger.info(f"BACKGROUND_TASK: Starting data sync for A-share: {symbol}")
    
    fund_data = await run_in_threadpool(a_share_fetcher.fetch_fundamental_data_from_baostock, symbol)
    if fund_data:
        await run_in_threadpool(db_writer.store_fundamental_data, db, symbol, fund_data)
        logger.info(f"Successfully synced fundamental data for {symbol}.")

    actions_data = await run_in_threadpool(a_share_fetcher.fetch_corporate_actions_from_baostock, symbol)
    if actions_data:
        count = await run_in_threadpool(db_writer.store_corporate_actions, db, symbol, actions_data)
        logger.info(f"Successfully synced {count} corporate actions for {symbol}.")

    earnings_data = await run_in_threadpool(a_share_fetcher.fetch_annual_net_profit_from_baostock, symbol)
    if earnings_data:
        count = await run_in_threadpool(db_writer.store_annual_earnings, db, symbol, earnings_data)
        logger.info(f"Successfully synced {count} annual earnings records for {symbol}.")


async def _sync_us_stock_data(db: Session, symbol: str):
    """Syncs all financial data for a US stock."""
    logger.info(f"BACKGROUND_TASK: Starting data sync for US stock: {symbol}")

    fund_data = await run_in_threadpool(us_stock_fetcher.fetch_us_fundamental_data_from_yfinance, symbol)
    if fund_data:
        await run_in_threadpool(db_writer.store_fundamental_data, db, symbol, fund_data)
        logger.info(f"Successfully synced fundamental data for {symbol}.")

    actions_data = await run_in_threadpool(us_stock_fetcher.fetch_us_corporate_actions_from_yfinance, symbol)
    if actions_data:
        count = await run_in_threadpool(db_writer.store_corporate_actions, db, symbol, actions_data)
        logger.info(f"Successfully synced {count} corporate actions for {symbol}.")

    earnings_data = await run_in_threadpool(us_stock_fetcher.fetch_us_annual_earnings_from_yfinance, symbol)
    if earnings_data:
        count = await run_in_threadpool(db_writer.store_annual_earnings, db, symbol, earnings_data)
        logger.info(f"Successfully synced {count} annual earnings records for {symbol}.")


def get_fundamental_data_from_db(db: Session, symbol: str) -> Optional[models.FundamentalData]:
    return db.query(models.FundamentalData).filter(models.FundamentalData.symbol == symbol).first()

def get_corporate_actions_from_db(db: Session, symbol: str) -> list[models.CorporateAction]:
    return db.query(models.CorporateAction).filter(models.CorporateAction.symbol == symbol).order_by(models.CorporateAction.ex_date).all()

def get_annual_earnings_from_db(db: Session, symbol: str) -> list[models.AnnualEarnings]:
    return db.query(models.AnnualEarnings).filter(models.AnnualEarnings.symbol == symbol).order_by(models.AnnualEarnings.year).all()

def resolve_symbol(db: Session, symbol: str) -> Optional[str]:
    """
    Resolves a potentially incomplete stock symbol to its full ts_code.
    """
    if '.' in symbol:
        return symbol
    
    a_share_info = db.query(models.StockInfo).filter(
        models.StockInfo.market_type == 'A_share',
        models.StockInfo.ts_code.ilike(f"{symbol}.%")
    ).first()
    if a_share_info:
        return a_share_info.ts_code

    us_stock_info = db.query(models.StockInfo).filter(
        models.StockInfo.market_type == 'US_stock',
        models.StockInfo.ts_code.ilike(symbol)
    ).first()
    if us_stock_info:
        return us_stock_info.ts_code
    
    if not any(char.isdigit() for char in symbol):
        return symbol.upper()

    logger.warning(f"Could not resolve symbol: {symbol}")
    return None