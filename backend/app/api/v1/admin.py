from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi_cache import FastAPICache

from app.db.session import get_db
from app.services import db_admin

router = APIRouter()

@router.post("/clear-cache", status_code=200)
async def clear_cache(db: Session = Depends(get_db)):
    """
    Endpoint to clear all cached financial data from the database and Redis.
    Intended for development and testing purposes.
    """
    try:
        # Clear database cache
        db_result = db_admin.clear_all_financial_data(db)
        
        # Clear Redis cache
        await FastAPICache.clear()
        
        db_result['message'] = "All database and Redis cache has been cleared successfully."
        return db_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
