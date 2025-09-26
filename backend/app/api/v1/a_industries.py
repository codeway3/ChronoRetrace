import logging
import math
from typing import cast

from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from starlette.concurrency import run_in_threadpool

from app.data.fetchers import a_industries_fetcher as fetcher
from app.schemas.industry import ConstituentStock

router = APIRouter()
logger = logging.getLogger(__name__)


def clean_json_data(data: list[dict]) -> list[dict]:
    """Recursively clean data to make it JSON compliant."""
    for item in data:
        for key, value in item.items():
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                item[key] = None
    return data


@router.get("/overview", response_model=list[dict[str, object]])
async def get_industry_overview(
    window: str = Query("20D", enum=["5D", "20D", "60D"]),
    provider: str = Query("em", enum=["em", "ths"]),
):
    """
    Get an overview of all industries from the default provider (Eastmoney).
    The data is cached for 1 hour.
    """
    try:
        logger.info(f"Fetching industry overview: window={window}, provider={provider}")
        data = cast(
            "list[dict[str, object]]", await fetcher.build_overview(window, provider)
        )
        logger.info(f"Industry overview fetched: count={len(data)}")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch industry overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to fetch industry overview"
        ) from e


@router.get("/{industry_code}/stocks", response_model=list[ConstituentStock])
@cache(expire=3600)
async def get_industry_constituent_stocks(industry_code: str):
    """
    Get the constituent stocks for a given industry from Eastmoney.
    The data is cached for 1 hour.
    """
    try:
        logger.info(f"Fetching constituents for industry: {industry_code}")
        data = await run_in_threadpool(
            fetcher.fetch_industry_constituents, industry_code=industry_code
        )

        if not data:
            logger.warning(f"No constituent stocks found for industry: {industry_code}")
            return []

        # Clean data to ensure JSON compliance
        cleaned_data = clean_json_data(data)

        logger.info(
            f"Fetched {len(cleaned_data)} constituents for industry: {industry_code}"
        )
        return cleaned_data
    except Exception as e:
        logger.error(
            f"Failed to fetch constituent stocks for industry {industry_code}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to fetch constituent stocks"
        ) from e
