from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime
import logging
import pandas as pd
from app.db import models

logger = logging.getLogger(__name__)


def store_stock_data(db: Session, ts_code: str, interval: str, df: pd.DataFrame):
    """
    Stores or updates (upserts) stock K-line data in the database.
    """
    if df.empty:
        return 0

    records_to_insert = df.to_dict('records')
    for record in records_to_insert:
        record['ts_code'] = ts_code
        record['interval'] = interval
        # Ensure trade_date is in the correct format if it's not already
        if isinstance(record['trade_date'], str):
            record['trade_date'] = datetime.strptime(record['trade_date'], '%Y-%m-%d').date()

    if not records_to_insert:
        return 0

    # Using SQLAlchemy's ORM bulk_insert_mappings for efficiency with upsert logic
    # This requires getting the dialect to choose the correct insert statement
    dialect = db.bind.dialect.name
    if dialect == 'sqlite':
        stmt = sqlite_insert(models.StockData).values(records_to_insert)
        # Define what to do on conflict: update the existing row
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ['ts_code', 'trade_date', 'interval']}
        stmt = stmt.on_conflict_do_update(
            index_elements=['ts_code', 'trade_date', 'interval'],
            set_=update_dict
        )
    else: # Assuming postgresql for production
        stmt = pg_insert(models.StockData).values(records_to_insert)
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ['ts_code', 'trade_date', 'interval']}
        stmt = stmt.on_conflict_do_update(
            index_elements=['ts_code', 'trade_date', 'interval'],
            set_=update_dict
        )
    
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def store_corporate_actions(db: Session, symbol: str, actions_data: list[dict]):
    """
    Stores or updates corporate actions data in the database.
    """
    if not actions_data:
        return 0

    actions_to_insert = []
    for item in actions_data:
        actions_to_insert.append({
            "symbol": symbol,
            "action_type": item["action_type"],
            "ex_date": item["ex_date"],
            "value": item["value"],
        })

    if not actions_to_insert:
        return 0

    if db.bind.dialect.name == 'sqlite':
        stmt = sqlite_insert(models.CorporateAction).values(actions_to_insert)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['symbol', 'ex_date', 'action_type']
        )
    else:
        stmt = pg_insert(models.CorporateAction).values(actions_to_insert)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['symbol', 'ex_date', 'action_type']
        )
    
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def store_fundamental_data(db: Session, symbol: str, data: dict):
    """
    Stores or updates fundamental data in the database using an upsert operation.
    """
    if not data:
        logger.warning(f"No fundamental data provided for symbol {symbol}. Skipping store operation.")
        return 0

    data['symbol'] = symbol
    data['last_updated'] = datetime.utcnow()

    insert_values = data.copy()
    update_values = {key: value for key, value in data.items() if key != 'symbol'}


    if db.bind.dialect.name == 'sqlite':
        stmt = sqlite_insert(models.FundamentalData).values(insert_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=['symbol'],
            set_=update_values
        )
    else:
        stmt = pg_insert(models.FundamentalData).values(insert_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=['symbol'],
            set_=update_values
        )

    try:
        result = db.execute(stmt)
        db.commit()
        logger.info(f"Successfully upserted fundamental data for {symbol}.")
        return result.rowcount
    except Exception as e:
        logger.error(f"Database error while upserting fundamental data for {symbol}: {e}")
        db.rollback()
        raise


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
