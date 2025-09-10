#!/usr/bin/env python3
"""
ChronoRetrace - 缓存管理API

本模块提供缓存管理相关的API端点，包括缓存预热、清理和状态查询等功能。

Author: ChronoRetrace Team
Date: 2024
"""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.infrastructure.cache.cache_service import cache_service
from app.infrastructure.cache.cache_warming import cache_warming_service
from app.infrastructure.monitoring.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


class CacheWarmingRequest(BaseModel):
    """缓存预热请求模型"""

    stock_codes: list[str] | None = None
    force_refresh: bool = False
    warm_hot_stocks: bool = True
    warm_stock_info: bool = True
    warm_recent_data: bool = True


class CacheStatsResponse(BaseModel):
    """缓存统计响应模型"""

    total_keys: int
    memory_usage: str
    hit_rate: float
    miss_rate: float
    warming_stats: dict
    last_warming_time: datetime | None


class CacheClearRequest(BaseModel):
    """缓存清理请求模型"""

    pattern: str | None = None
    clear_all: bool = False


@router.post("/warm")
async def warm_cache(request: CacheWarmingRequest, background_tasks: BackgroundTasks):
    """
    执行缓存预热

    Args:
        request: 缓存预热请求参数
        background_tasks: 后台任务管理器

    Returns:
        Dict: 预热任务状态
    """
    try:
        # 记录预热开始时间
        start_time = datetime.now()

        # 在后台执行缓存预热
        if request.stock_codes:
            # 预热指定股票
            background_tasks.add_task(
                cache_warming_service.warm_specific_stocks,
                request.stock_codes,
                request.force_refresh,
            )
        else:
            # 执行完整预热
            background_tasks.add_task(
                cache_warming_service.warm_cache, request.force_refresh
            )

        # 记录性能指标
        performance_monitor.record_api_metric(
            endpoint="/cache/warm",
            method="POST",
            status_code=200,
            response_time=0.0,  # 后台任务，响应时间为0
        )

        return {
            "status": "success",
            "message": "缓存预热任务已启动",
            "task_started_at": start_time,
            "warming_config": {
                "stock_codes": request.stock_codes,
                "force_refresh": request.force_refresh,
                "warm_hot_stocks": request.warm_hot_stocks,
                "warm_stock_info": request.warm_stock_info,
                "warm_recent_data": request.warm_recent_data,
            },
        }

    except Exception as e:
        logger.error(f"缓存预热失败: {e}")
        raise HTTPException(status_code=500, detail=f"缓存预热失败: {str(e)}") from e


@router.get("/stats")
async def get_cache_stats() -> CacheStatsResponse:
    """
    获取缓存统计信息

    Returns:
        CacheStatsResponse: 缓存统计数据
    """
    try:
        # 获取缓存统计
        cache_stats = cache_service.get_cache_stats()
        warming_stats = cache_warming_service.get_warming_stats()

        return CacheStatsResponse(
            total_keys=cache_stats.get("total_keys", 0),
            memory_usage=cache_stats.get("memory_usage", "0MB"),
            hit_rate=cache_stats.get("hit_rate", 0.0),
            miss_rate=cache_stats.get("miss_rate", 0.0),
            warming_stats=warming_stats,
            last_warming_time=warming_stats.get("last_warming_time"),
        )

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取缓存统计失败: {str(e)}"
        ) from e


@router.post("/clear")
async def clear_cache(request: CacheClearRequest):
    """
    清理缓存

    Args:
        request: 缓存清理请求参数

    Returns:
        Dict: 清理结果
    """
    try:
        if request.clear_all:
            # 清理所有缓存
            cleared_count = cache_service.clear_all()
            message = f"已清理所有缓存，共 {cleared_count} 个键"
        elif request.pattern:
            # 按模式清理缓存
            cleared_count = cache_service.clear_by_pattern(request.pattern)
            message = (
                f"已清理匹配模式 '{request.pattern}' 的缓存，共 {cleared_count} 个键"
            )
        else:
            raise HTTPException(
                status_code=400, detail="必须指定清理模式或清理所有缓存"
            )

        # 记录性能指标
        performance_monitor.record_api_metric(
            endpoint="/cache/clear", method="POST", status_code=200, response_time=0.0
        )

        return {
            "status": "success",
            "message": message,
            "cleared_count": cleared_count,
            "cleared_at": datetime.now(),
        }

    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}") from e


@router.post("/refresh")
async def refresh_cache(
    stock_codes: list[str] | None = None, background_tasks: BackgroundTasks = None
):
    """
    刷新缓存数据

    Args:
        stock_codes: 要刷新的股票代码列表，为空则刷新所有
        background_tasks: 后台任务管理器

    Returns:
        Dict: 刷新任务状态
    """
    try:
        start_time = datetime.now()

        if stock_codes:
            # 刷新指定股票的缓存
            background_tasks.add_task(
                cache_warming_service.refresh_stock_cache, stock_codes
            )
            message = f"已启动 {len(stock_codes)} 只股票的缓存刷新任务"
        else:
            # 刷新所有缓存
            background_tasks.add_task(cache_warming_service.refresh_all_cache)
            message = "已启动全量缓存刷新任务"

        return {
            "status": "success",
            "message": message,
            "task_started_at": start_time,
            "stock_codes": stock_codes,
        }

    except Exception as e:
        logger.error(f"刷新缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"刷新缓存失败: {str(e)}") from e


@router.get("/health")
async def cache_health_check():
    """
    缓存健康检查

    Returns:
        Dict: 健康状态信息
    """
    try:
        # 检查Redis连接
        redis_status = cache_service.health_check()

        # 检查缓存预热服务状态
        warming_status = cache_warming_service.is_healthy()

        overall_status = "healthy" if redis_status and warming_status else "unhealthy"

        return {
            "status": overall_status,
            "redis_status": "connected" if redis_status else "disconnected",
            "warming_service_status": "active" if warming_status else "inactive",
            "checked_at": datetime.now(),
        }

    except Exception as e:
        logger.error(f"缓存健康检查失败: {e}")
        return {"status": "unhealthy", "error": str(e), "checked_at": datetime.now()}
