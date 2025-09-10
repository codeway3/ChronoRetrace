import logging
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.infrastructure.database import models

from ..quality.quality_manager import DataQualityConfig, DataQualityManager

logger = logging.getLogger(__name__)


def store_stock_data(db: Session, ts_code: str, interval: str, df: pd.DataFrame):
    """
    Stores or updates (upserts) stock K-line data in the database.
    Includes data quality validation and deduplication.
    """
    if df.empty:
        return 0

    # Apply data quality checks
    try:
        config = DataQualityConfig(
            enable_validation=True,
            enable_deduplication=True,
            validation_rules={
                "open": {"min_value": 0, "required": True},
                "high": {"min_value": 0, "required": True},
                "low": {"min_value": 0, "required": True},
                "close": {"min_value": 0, "required": True},
                "vol": {"min_value": 0},
                "trade_date": {"required": True},
            },
        )

        with DataQualityManager(config) as quality_manager:
            # Process the dataframe through quality checks
            quality_result = quality_manager.process_data(df)

            if quality_result.has_errors:
                logger.warning(
                    f"Data quality issues found for {ts_code}: {quality_result.validation_report.summary}"
                )
                # Log validation errors but continue with valid data
                for error in quality_result.validation_report.errors:
                    logger.error(f"Validation error: {error}")

            # Use the cleaned data from quality manager
            processed_df = quality_result.processed_data

            if processed_df.empty:
                logger.warning(
                    f"No valid data remaining after quality checks for {ts_code}"
                )
                return 0

            logger.info(
                f"Data quality summary for {ts_code}: {quality_result.deduplication_report.summary if quality_result.deduplication_report else 'No deduplication performed'}"
            )

    except Exception as e:
        logger.error(
            f"Data quality check failed for {ts_code}: {e}. Proceeding with original data."
        )
        processed_df = df

    records_to_insert = processed_df.to_dict(orient="records")
    for record in records_to_insert:
        record["ts_code"] = ts_code
        record["interval"] = interval
        # Ensure trade_date is in the correct format if it's not already
        if isinstance(record["trade_date"], str):
            record["trade_date"] = datetime.strptime(
                record["trade_date"], "%Y-%m-%d"
            ).date()

    if not records_to_insert:
        return 0

    # Using SQLAlchemy's ORM bulk_insert_mappings for efficiency with upsert logic
    # This requires getting the dialect to choose the correct insert statement
    if db.bind is None:
        raise ValueError("Database session is not bound to an engine")
    dialect = db.bind.dialect.name
    stmt: Any
    if dialect == "sqlite":
        sqlite_stmt = sqlite_insert(models.StockData).values(records_to_insert)
        # Define what to do on conflict: update the existing row
        update_dict = {
            c.name: c
            for c in sqlite_stmt.excluded
            if c.name not in ["ts_code", "trade_date", "interval"]
        }
        stmt = sqlite_stmt.on_conflict_do_update(
            index_elements=["ts_code", "trade_date", "interval"], set_=update_dict
        )
    else:  # Assuming postgresql for production
        pg_stmt = pg_insert(models.StockData).values(records_to_insert)
        update_dict = {
            c.name: c
            for c in pg_stmt.excluded
            if c.name not in ["ts_code", "trade_date", "interval"]
        }
        stmt = pg_stmt.on_conflict_do_update(
            index_elements=["ts_code", "trade_date", "interval"], set_=update_dict
        )

    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def store_corporate_actions(db: Session, symbol: str, actions_data: list[dict]):
    """
    Stores or updates corporate actions data in the database.
    Includes data quality validation and deduplication.
    """
    if not actions_data:
        return 0

    # Apply data quality checks for corporate actions
    try:
        config = DataQualityConfig(
            enable_validation=True,
            enable_deduplication=True,
            validation_rules={
                "action_type": {
                    "required": True,
                    "allowed_values": ["dividend", "split"],
                },
                "ex_date": {"required": True},
                "value": {"min_value": 0, "required": True},
            },
        )

        # Convert to DataFrame for processing
        df = pd.DataFrame(actions_data)
        df["symbol"] = symbol

        with DataQualityManager(config) as quality_manager:
            quality_result = quality_manager.process_data(df)

            if quality_result.has_errors:
                logger.warning(
                    f"Corporate actions data quality issues for {symbol}: {quality_result.validation_report.summary}"
                )
                for error in quality_result.validation_report.errors:
                    logger.error(f"Validation error: {error}")

            if quality_result.processed_data.empty:
                logger.warning(
                    f"No valid corporate actions remaining after quality checks for {symbol}"
                )
                return 0

            # Convert back to list of dicts
            processed_actions = quality_result.processed_data.to_dict(orient="records")

    except Exception as e:
        logger.error(
            f"Data quality check failed for corporate actions {symbol}: {e}. Proceeding with original data."
        )
        processed_actions = actions_data

    actions_to_insert = []
    for item in processed_actions:
        actions_to_insert.append(
            {
                "symbol": symbol,
                "action_type": item["action_type"],
                "ex_date": item["ex_date"],
                "value": item["value"],
            }
        )

    if not actions_to_insert:
        return 0

    stmt: Any
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        sqlite_stmt = sqlite_insert(models.CorporateAction).values(actions_to_insert)
        stmt = sqlite_stmt.on_conflict_do_nothing(
            index_elements=["symbol", "ex_date", "action_type"]
        )
    else:
        pg_stmt = pg_insert(models.CorporateAction).values(actions_to_insert)
        stmt = pg_stmt.on_conflict_do_nothing(
            index_elements=["symbol", "ex_date", "action_type"]
        )

    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def store_fundamental_data(db: Session, symbol: str, data: dict):
    """
    Stores or updates fundamental data in the database using an upsert operation.
    Includes data quality validation.
    """
    if not data:
        logger.warning(
            f"No fundamental data provided for symbol {symbol}. Skipping store operation."
        )
        return 0

    # Apply data quality checks for fundamental data
    try:
        config = DataQualityConfig(
            enable_validation=True,
            enable_deduplication=False,  # Fundamental data is typically unique per symbol
            validation_rules={
                "market_cap": {"min_value": 0},
                "pe_ratio": {"min_value": 0},
                "eps": {"allow_negative": True},
                "beta": {"allow_negative": True},
                "dividend_yield": {"min_value": 0, "max_value": 100},
            },
        )

        # Convert dict to DataFrame for processing
        df = pd.DataFrame([data])

        with DataQualityManager(config) as quality_manager:
            quality_result = quality_manager.validate_only(df)

            if quality_result.has_errors:
                logger.warning(
                    f"Fundamental data quality issues for {symbol}: {quality_result.validation_report.summary}"
                )
                for error in quality_result.validation_report.errors:
                    logger.error(f"Validation error: {error}")

            # Use the validated data
            processed_data = (
                quality_result.processed_data.iloc[0].to_dict()  # type: ignore[misc]
                if not quality_result.processed_data.empty
                else data
            )

    except Exception as e:
        logger.error(
            f"Data quality check failed for fundamental data {symbol}: {e}. Proceeding with original data."
        )
        processed_data = data

    processed_data["symbol"] = symbol
    processed_data["last_updated"] = datetime.utcnow()

    insert_values = processed_data.copy()
    update_values = {
        key: value for key, value in processed_data.items() if key != "symbol"
    }

    stmt: Any
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        sqlite_stmt = sqlite_insert(models.FundamentalData).values(insert_values)
        stmt = sqlite_stmt.on_conflict_do_update(
            index_elements=["symbol"], set_=update_values
        )
    else:
        pg_stmt = pg_insert(models.FundamentalData).values(insert_values)
        stmt = pg_stmt.on_conflict_do_update(
            index_elements=["symbol"], set_=update_values
        )

    try:
        result = db.execute(stmt)
        db.commit()
        logger.info(f"Successfully upserted fundamental data for {symbol}.")
        return result.rowcount
    except Exception as e:
        logger.error(
            f"Database error while upserting fundamental data for {symbol}: {e}"
        )
        db.rollback()
        raise


def store_annual_earnings(db: Session, symbol: str, annual_earnings_data: list[dict]):
    """
    Stores or updates annual earnings data in the database.
    Includes data quality validation and deduplication.
    """
    if not annual_earnings_data:
        return 0

    # Apply data quality checks for annual earnings
    try:
        config = DataQualityConfig(
            enable_validation=True,
            enable_deduplication=True,
            validation_rules={
                "year": {"required": True, "min_value": 1900, "max_value": 2100},
                "net_profit": {"required": True, "allow_negative": True},
            },
        )

        # Convert to DataFrame for processing
        df = pd.DataFrame(annual_earnings_data)
        df["symbol"] = symbol

        with DataQualityManager(config) as quality_manager:
            quality_result = quality_manager.process_data(df)

            if quality_result.has_errors:
                logger.warning(
                    f"Annual earnings data quality issues for {symbol}: {quality_result.validation_report.summary}"
                )
                for error in quality_result.validation_report.errors:
                    logger.error(f"Validation error: {error}")

            if quality_result.processed_data.empty:
                logger.warning(
                    f"No valid annual earnings remaining after quality checks for {symbol}"
                )
                return 0

            # Convert back to list of dicts
            processed_earnings = quality_result.processed_data.to_dict(orient="records")

    except Exception as e:
        logger.error(
            f"Data quality check failed for annual earnings {symbol}: {e}. Proceeding with original data."
        )
        processed_earnings = annual_earnings_data

    earnings_to_insert = []
    for item in processed_earnings:
        earnings_to_insert.append(
            {
                "symbol": symbol,
                "year": item["year"],
                "net_profit": item["net_profit"],
                "last_updated": datetime.utcnow(),
            }
        )

    stmt: Any
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        sqlite_stmt = sqlite_insert(models.AnnualEarnings).values(earnings_to_insert)
        stmt = sqlite_stmt.on_conflict_do_update(
            index_elements=["symbol", "year"],
            set_={
                "net_profit": sqlite_stmt.excluded.net_profit,
                "last_updated": sqlite_stmt.excluded.last_updated,
            },
        )
    else:
        pg_stmt = pg_insert(models.AnnualEarnings).values(earnings_to_insert)
        stmt = pg_stmt.on_conflict_do_update(
            index_elements=["symbol", "year"],
            set_={
                "net_profit": pg_stmt.excluded.net_profit,
                "last_updated": pg_stmt.excluded.last_updated,
            },
        )

    result = db.execute(stmt)
    db.commit()
    return result.rowcount
