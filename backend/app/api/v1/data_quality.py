import logging
from datetime import datetime
from typing import Any, Union

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

from app.data.quality.deduplication_service import DeduplicationStrategy
from app.data.quality.quality_manager import DataQualityConfig, DataQualityManager
from app.infrastructure.database.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/validate")
async def validate_data(
    data: list[dict[str, Any]],
    validation_rules: Union[dict[str, dict[str, Any]], None] = None,
    db: Session = Depends(get_db),
):
    """
    Validate data using custom validation rules.
    """
    try:
        config = DataQualityConfig(
            enable_validation=True,
            enable_deduplication=False,
            validation_rules=validation_rules or {},
        )

        df = pd.DataFrame(data)

        with DataQualityManager(db, config) as quality_manager:
            result = quality_manager.validate_only(df)

            return {
                "status": "success",
                "has_errors": result.has_errors,
                "validation_report": {
                    "summary": result.validation_report.summary,
                    "total_records": result.validation_report.total_records,
                    "valid_records": result.validation_report.valid_records,
                    "invalid_records": result.validation_report.invalid_records,
                    "errors": result.validation_report.errors,
                    "warnings": result.validation_report.warnings,
                },
                "processed_data": (
                    result.processed_data.to_dict(orient="records")
                    if not result.processed_data.empty
                    else []
                ),
            }

    except Exception as e:
        logger.error(f"Data validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Validation failed: {str(e)}"
        ) from e


@router.post("/deduplicate")
async def deduplicate_data(
    data: list[dict[str, Any]],
    deduplication_fields: list[str],
    strategy: str = Query(
        "KEEP_FIRST", enum=["KEEP_FIRST", "KEEP_LAST", "KEEP_HIGHEST_QUALITY"]
    ),
    db: Session = Depends(get_db),
):
    """
    Remove duplicates from data using specified strategy.
    """
    try:
        config = DataQualityConfig(
            enable_validation=False,
            enable_deduplication=True,
            deduplication_strategy=DeduplicationStrategy(strategy),
        )

        df = pd.DataFrame(data)

        with DataQualityManager(db, config) as quality_manager:
            result = quality_manager.deduplicate_only(df)

            return {
                "status": "success",
                "deduplication_report": (
                    {
                        "summary": result.deduplication_report.summary,
                        "total_records": result.deduplication_report.total_records,
                        "unique_records": result.deduplication_report.unique_records,
                        "duplicate_records": result.deduplication_report.duplicate_records,
                        "duplicates_removed": result.deduplication_report.duplicates_removed,
                    }
                    if result.deduplication_report
                    else None
                ),
                "processed_data": (
                    result.processed_data.to_dict(orient="records")
                    if not result.processed_data.empty
                    else []
                ),
            }

    except Exception as e:
        logger.error(f"Data deduplication failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Deduplication failed: {str(e)}"
        ) from e


@router.post("/process")
async def process_data(
    data: list[dict[str, Any]],
    validation_rules: Union[dict[str, dict[str, Any]], None] = None,
    deduplication_fields: Union[list[str], None] = None,
    strategy: str = Query(
        "KEEP_FIRST", enum=["KEEP_FIRST", "KEEP_LAST", "KEEP_HIGHEST_QUALITY"]
    ),
    db: Session = Depends(get_db),
):
    """
    Process data with both validation and deduplication.
    """
    try:
        config = DataQualityConfig(
            enable_validation=bool(validation_rules),
            enable_deduplication=bool(deduplication_fields),
            validation_rules=validation_rules or {},
            deduplication_strategy=DeduplicationStrategy(strategy),
        )

        df = pd.DataFrame(data)

        with DataQualityManager(db, config) as quality_manager:
            result = quality_manager.process_data(df)

            response = {
                "status": "success",
                "has_errors": result.has_errors,
                "processed_data": (
                    result.processed_data.to_dict(orient="records")
                    if not result.processed_data.empty
                    else []
                ),
            }

            if result.validation_report:
                response["validation_report"] = {
                    "summary": result.validation_report.summary,
                    "total_records": result.validation_report.total_records,
                    "valid_records": result.validation_report.valid_records,
                    "invalid_records": result.validation_report.invalid_records,
                    "errors": result.validation_report.errors,
                    "warnings": result.validation_report.warnings,
                }

            if result.deduplication_report:
                response["deduplication_report"] = {
                    "summary": result.deduplication_report.summary,
                    "total_records": result.deduplication_report.total_records,
                    "unique_records": result.deduplication_report.unique_records,
                    "duplicate_records": result.deduplication_report.duplicate_records,
                    "duplicates_removed": result.deduplication_report.duplicates_removed,
                }

            return response

    except Exception as e:
        logger.error(f"Data processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Processing failed: {str(e)}"
        ) from e


@router.get("/health")
@cache(expire=300)  # Cache for 5 minutes
async def data_quality_health(db: Session = Depends(get_db)):
    """
    Check the health status of data quality services.
    """
    try:
        # Test basic functionality
        test_data = pd.DataFrame([{"test": 1, "value": 100}])
        config = DataQualityConfig(
            enable_validation=True,
            enable_deduplication=True,
            validation_rules={"test": {"required": True}},
        )

        with DataQualityManager(db, config) as quality_manager:
            result = quality_manager.process_data(test_data)

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "validation": "operational",
                "deduplication": "operational",
                "performance_optimization": "operational",
            },
            "test_result": {
                "processed_records": result.total_records,
                "valid_records": result.valid_records,
                "invalid_records": result.invalid_records,
                "has_errors": len(result.error_messages) > 0,
                "quality_score": result.quality_score,
            },
        }

    except Exception as e:
        logger.error(f"Data quality health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@router.get("/metrics")
@cache(expire=60)  # Cache for 1 minute
async def get_data_quality_metrics():
    """
    Get data quality metrics and statistics.
    """
    try:
        # This would typically query a metrics store or database
        # For now, return mock metrics
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_metrics": {
                "total_validations_today": 0,
                "validation_success_rate": 0.0,
                "common_validation_errors": [],
            },
            "deduplication_metrics": {
                "total_deduplications_today": 0,
                "average_duplicate_rate": 0.0,
                "total_duplicates_removed": 0,
            },
            "performance_metrics": {
                "average_processing_time_ms": 0.0,
                "memory_usage_mb": 0.0,
                "cache_hit_rate": 0.0,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get data quality metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get metrics: {str(e)}"
        ) from e
