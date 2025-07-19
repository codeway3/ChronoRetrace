from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import db_admin

router = APIRouter()

@router.post("/clear-cache", status_code=200)
def clear_cache(db: Session = Depends(get_db)):
    """
    Endpoint to clear all cached financial data from the database.
    Intended for development and testing purposes.
    """
    try:
        result = db_admin.clear_all_financial_data(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
