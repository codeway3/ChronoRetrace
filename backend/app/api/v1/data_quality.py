import logging
from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

from app.data.quality.deduplication_service import DeduplicationStrategy
from app.data.quality.quality_manager import DataQualityConfig, DataQualityManager
from app.infrastructure.database.session import get_db
from starlette.concurrency import run_in_threadpool

import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局并发限制：同一时间最多处理 2 个数据质量任务，可根据需要调整
DATA_QUALITY_SEMAPHORE = asyncio.Semaphore(2)


@router.post("/validate")
async def validate_data(
    data: list[dict[str, Any]],
    validation_rules: dict[str, dict[str, Any]] | None = None,
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

        # 直接使用 list[dict], validate_only 需要列表而非 DataFrame
        with DataQualityManager(db, config) as quality_manager:
            reports = quality_manager.validate_only(data)

            valid_count = sum(1 for r in reports if r.is_valid)
            invalid_count = len(reports) - valid_count
            errors = [err for r in reports for err in (r.errors or [])]
            warnings = [w for r in reports for w in (r.warnings or [])]

            return {
                "status": "success",
                "has_errors": (invalid_count > 0) or (len(errors) > 0),
                "validation_report": {
                    "summary": f"校验汇总: 有效 {valid_count} 条, 无效 {invalid_count} 条",
                    "total_records": len(reports),
                    "valid_records": valid_count,
                    "invalid_records": invalid_count,
                    "errors": errors,
                    "warnings": warnings,
                },
                # 校验接口不做加工, 返回空列表以保持兼容
                "processed_data": [],
            }

    except Exception as e:
        logger.exception("Data validation failed")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e!s}") from e


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

        # 直接使用 list[dict], deduplicate_only 需要列表而非 DataFrame
        with DataQualityManager(db, config) as quality_manager:
            report = quality_manager.deduplicate_only(data)

            return {
                "status": "success",
                "requested_fields": deduplication_fields,
                "deduplication_report": (
                    {
                        "summary": report.summary,
                        "total_processed": report.total_processed,
                        "duplicates_found": report.duplicates_found,
                        "duplicates_removed": report.duplicates_removed,
                        "duplicate_groups": len(report.duplicate_groups),
                    }
                    if report
                    else None
                ),
                "processed_data": (
                    report.deduplicated_data
                    if report and report.deduplicated_data is not None
                    else data
                ),
            }

    except Exception as e:
        logger.exception("Data deduplication failed")
        raise HTTPException(
            status_code=500, detail=f"Deduplication failed: {e!s}"
        ) from e


@router.post("/process")
async def process_data(
    data: list[dict[str, Any]],
    validation_rules: dict[str, dict[str, Any]] | None = None,
    deduplication_fields: list[str] | None = None,
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

        # 直接传入列表, process_data 可接受列表或 DataFrame
        with DataQualityManager(db, config) as quality_manager:
            result = quality_manager.process_data(data)

            response = {
                "status": "success",
                "has_errors": result.has_errors,
                "processed_data": (
                    result.deduplication_report.deduplicated_data
                    if result.deduplication_report
                    and result.deduplication_report.deduplicated_data is not None
                    else data
                ),
            }

            if result.validation_reports:
                valid_count = result.valid_records
                invalid_count = result.invalid_records
                errors = [
                    err for r in result.validation_reports for err in (r.errors or [])
                ]
                warnings = [
                    w for r in result.validation_reports for w in (r.warnings or [])
                ]

                response["validation_report"] = {
                    "summary": (
                        f"校验汇总: 有效 {valid_count} 条, 无效 {invalid_count} 条"
                    ),
                    "total_records": result.total_records,
                    "valid_records": valid_count,
                    "invalid_records": invalid_count,
                    "errors": errors,
                    "warnings": warnings,
                }

            if result.deduplication_report:
                report = result.deduplication_report
                response["deduplication_report"] = {
                    "summary": report.summary,
                    "total_processed": report.total_processed,
                    "duplicates_found": report.duplicates_found,
                    "duplicates_removed": report.duplicates_removed,
                    "duplicate_groups": len(report.duplicate_groups),
                }

            return response

    except Exception as e:
        logger.exception("Data processing failed")
        raise HTTPException(status_code=500, detail=f"Processing failed: {e!s}") from e


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
        logger.exception("Data quality health check failed")
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
        logger.exception("Failed to get data quality metrics")
        raise HTTPException(
            status_code=500, detail=f"Failed to get metrics: {e!s}"
        ) from e
