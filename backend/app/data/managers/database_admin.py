import logging

from sqlalchemy.orm import Session

from app.infrastructure.database import models

logger = logging.getLogger(__name__)


def clear_all_financial_data(db: Session):
    """
    Deletes all records from financial data tables for caching purposes.
    This includes fundamental data, corporate actions, and annual earnings.
    The stock_info table is NOT cleared.
    """
    try:
        num_deleted_fundamentals = db.query(models.FundamentalData).delete()
        num_deleted_actions = db.query(models.CorporateAction).delete()
        num_deleted_earnings = db.query(models.AnnualEarnings).delete()

        db.commit()

        logger.info(f"Cleared {num_deleted_fundamentals} fundamental data records.")
        logger.info(f"Cleared {num_deleted_actions} corporate action records.")
        logger.info(f"Cleared {num_deleted_earnings} annual earning records.")

        return {
            "message": "All financial data cache has been cleared successfully.",
            "deleted_counts": {
                "fundamental_data": num_deleted_fundamentals,
                "corporate_actions": num_deleted_actions,
                "annual_earnings": num_deleted_earnings,
            },
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing financial data cache: {e}", exc_info=True)
        raise
