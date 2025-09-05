from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache import FastAPICache
from redis import asyncio as aioredis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.data.managers import database_admin as db_admin

router = APIRouter()


@router.get("/redis-health", status_code=200)
async def redis_health_check():
    """
    Checks the health of the Redis connection.
    """
    try:
        redis = await aioredis.from_url(settings.REDIS_URL)
        await redis.ping()
        await redis.close()
        return {"status": "ok", "message": "Redis connection is healthy."}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Redis connection failed.",
                "error_details": str(e),
            },
        )


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

        db_result["message"] = (
            "All database and Redis cache has been cleared successfully."
        )
        return db_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
