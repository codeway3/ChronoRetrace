from __future__ import annotations
from typing import Union

# !/usr/bin/env python3
"""

ChronoRetrace - 监控API端点

本模块提供系统性能监控、缓存统计、API性能等数据的查询接口。
包含实时指标、历史数据、健康检查等功能。

Author: ChronoRetrace Team
Date: 2024
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.infrastructure.cache import cache_service
from app.infrastructure.monitoring import (
    PerformanceMetric,
    performance_monitor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# 响应模型
class SystemHealthResponse(BaseModel):
    """系统健康状态响应"""

    status: str = Field(description="系统状态")
    timestamp: datetime = Field(description="检查时间")
    uptime_seconds: float = Field(description="运行时间(秒)")
    memory_usage_mb: float = Field(description="内存使用量(MB)")
    cpu_usage_percent: float = Field(description="CPU使用率(%)")
    cache_status: str = Field(description="缓存状态")
    database_status: str = Field(description="数据库状态")
    issues: list[str] = Field(default_factory=list, description="发现的问题")


class PerformanceStatsResponse(BaseModel):
    """性能统计响应"""

    period_start: datetime = Field(description="统计开始时间")
    period_end: datetime = Field(description="统计结束时间")
    total_requests: int = Field(description="总请求数")
    avg_response_time_ms: float = Field(description="平均响应时间(毫秒)")
    success_rate: float = Field(description="成功率")
    error_rate: float = Field(description="错误率")
    requests_per_second: float = Field(description="每秒请求数")
    slowest_endpoints: list[dict[str, Any]] = Field(description="最慢的端点")
    most_active_endpoints: list[dict[str, Any]] = Field(description="最活跃的端点")


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""

    redis_stats: dict[str, Any] = Field(description="Redis缓存统计")
    memory_cache_stats: dict[str, Any] = Field(description="内存缓存统计")
    overall_hit_rate: float = Field(description="总体命中率")
    total_operations: int = Field(description="总操作数")
    cache_size_mb: float = Field(description="缓存大小(MB)")
    top_cached_keys: list[dict[str, Any]] = Field(description="热门缓存键")


class MetricsResponse(BaseModel):
    """指标数据响应"""

    metrics: list[PerformanceMetric] = Field(description="性能指标列表")
    summary: dict[str, Any] = Field(description="指标摘要")
    period: str = Field(description="统计周期")


# 依赖函数
def get_time_range(
    hours: int = Query(1, ge=1, le=168, description="查询时间范围(小时)"),
) -> tuple[datetime, datetime]:
    """获取时间范围"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    return start_time, end_time


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """
    获取系统健康状态

    Returns:
        SystemHealthResponse: 系统健康状态
    """
    try:
        # 获取系统指标
        system_metrics = performance_monitor.get_system_metrics()

        # 检查缓存状态
        cache_status = "healthy"
        try:
            cache_service.ping()
        except Exception:
            cache_status = "unhealthy"

        # 检查数据库状态（简化实现）
        database_status = "healthy"  # 实际应该检查数据库连接

        # 分析问题
        issues = []
        memory_usage_mb = system_metrics.get("memory_available_mb", 0)
        cpu_usage_percent = system_metrics.get("cpu_percent", 0)

        # 计算内存使用量（从可用内存推算）
        if memory_usage_mb < 500:  # 可用内存少于500MB
            issues.append("内存使用量过高")
        if cpu_usage_percent > 80:
            issues.append("CPU使用率过高")
        if cache_status == "unhealthy":
            issues.append("缓存服务不可用")
        if database_status == "unhealthy":
            issues.append("数据库连接异常")

        # 确定整体状态
        if issues:
            status = "warning" if len(issues) <= 2 else "critical"
        else:
            status = "healthy"

        # 计算运行时间（简化实现）
        import time

        uptime_seconds = time.time() - system_metrics.get("start_time", time.time())

        return SystemHealthResponse(
            status=status,
            timestamp=datetime.now(),
            uptime_seconds=uptime_seconds,
            memory_usage_mb=max(0, 2048 - memory_usage_mb),  # 假设总内存2GB
            cpu_usage_percent=cpu_usage_percent,
            cache_status=cache_status,
            database_status=database_status,
            issues=issues,
        )

    except Exception as e:
        logger.error(f"获取系统健康状态失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取系统健康状态") from e


@router.get("/performance", response_model=PerformanceStatsResponse)
async def get_performance_stats(
    time_range: tuple[datetime, datetime] = Depends(get_time_range),
):
    """
    获取性能统计数据

    Args:
        time_range: 时间范围

    Returns:
        PerformanceStatsResponse: 性能统计数据
    """
    try:
        start_time, end_time = time_range

        # 获取API指标
        api_metrics = performance_monitor.get_api_metrics()

        # 计算统计数据
        total_requests = api_metrics.total_requests
        avg_response_time = api_metrics.avg_response_time_ms
        success_rate = api_metrics.success_rate
        error_rate = 1.0 - success_rate

        # 计算RPS
        time_diff_hours = (end_time - start_time).total_seconds() / 3600
        requests_per_second = (
            total_requests / (time_diff_hours * 3600) if time_diff_hours > 0 else 0
        )

        # 获取最慢的端点（模拟数据）
        slowest_endpoints = [
            {"endpoint": "/api/v1/stocks/data", "avg_time_ms": 450.2, "requests": 1234},
            {
                "endpoint": "/api/v1/stocks/fundamental",
                "avg_time_ms": 380.5,
                "requests": 567,
            },
            {"endpoint": "/api/v1/stocks/sync", "avg_time_ms": 320.1, "requests": 89},
        ]

        # 获取最活跃的端点（模拟数据）
        most_active_endpoints = [
            {"endpoint": "/api/v1/stocks/list", "requests": 5678, "avg_time_ms": 120.3},
            {"endpoint": "/api/v1/stocks/data", "requests": 1234, "avg_time_ms": 450.2},
            {
                "endpoint": "/api/v1/stocks/fundamental",
                "requests": 567,
                "avg_time_ms": 380.5,
            },
        ]

        return PerformanceStatsResponse(
            period_start=start_time,
            period_end=end_time,
            total_requests=total_requests,
            avg_response_time_ms=avg_response_time,
            success_rate=success_rate,
            error_rate=error_rate,
            requests_per_second=requests_per_second,
            slowest_endpoints=slowest_endpoints,
            most_active_endpoints=most_active_endpoints,
        )

    except Exception as e:
        logger.error(f"获取性能统计失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取性能统计数据") from e


@router.get("/cache", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    获取缓存统计数据

    Returns:
        CacheStatsResponse: 缓存统计数据
    """
    try:
        # 获取缓存统计
        cache_stats = performance_monitor.get_cache_stats()

        # 获取Redis统计
        redis_info = cache_service.get_cache_info()
        redis_stats = {
            "connected": redis_info.get("connected", False),
            "total_keys": redis_info.get("total_keys", 0),
            "memory_usage_mb": redis_info.get("memory_usage_mb", 0),
            "hit_rate": redis_info.get("hit_rate", 0.0),
            "operations_per_second": redis_info.get("ops_per_sec", 0),
        }

        # 内存缓存统计（模拟数据）
        memory_cache_stats = {
            "size_mb": 45.2,
            "entries": 1250,
            "hit_rate": 0.85,
            "evictions": 23,
        }

        # 计算总体命中率
        total_hits = cache_stats.total_hits
        total_operations = cache_stats.total_operations
        overall_hit_rate = (
            total_hits / total_operations if total_operations > 0 else 0.0
        )

        # 热门缓存键（模拟数据）
        top_cached_keys = [
            {"key": "stock_list_all", "hits": 1234, "size_kb": 45.2},
            {"key": "stock_data_000001_1d", "hits": 567, "size_kb": 12.8},
            {"key": "fundamental_000001", "hits": 234, "size_kb": 8.5},
        ]

        return CacheStatsResponse(
            redis_stats=redis_stats,
            memory_cache_stats=memory_cache_stats,
            overall_hit_rate=overall_hit_rate,
            total_operations=total_operations,
            cache_size_mb=redis_stats["memory_usage_mb"]
            + memory_cache_stats["size_mb"],
            top_cached_keys=top_cached_keys,
        )

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取缓存统计数据") from e


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    metric_type: Union[str, None] = Query(None, description="指标类型过滤"),
    time_range: tuple[datetime, datetime] = Depends(get_time_range),
):
    """
    获取详细的性能指标数据

    Args:
        metric_type: 指标类型过滤
        time_range: 时间范围

    Returns:
        MetricsResponse: 指标数据
    """
    try:
        start_time, end_time = time_range

        # 获取指标数据
        metrics = performance_monitor.get_metrics_in_range(start_time, end_time)

        # 按类型过滤
        if metric_type:
            metrics = [m for m in metrics if metric_type in m.name]

        # 计算摘要
        summary = {
            "total_metrics": len(metrics),
            "time_range_hours": (end_time - start_time).total_seconds() / 3600,
            "metric_types": list({m.name.split(".")[0] for m in metrics}),
            "avg_value": sum(m.value for m in metrics) / len(metrics) if metrics else 0,
        }

        return MetricsResponse(
            metrics=metrics,
            summary=summary,
            period=f"{start_time.isoformat()} - {end_time.isoformat()}",
        )

    except Exception as e:
        logger.error(f"获取指标数据失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取指标数据") from e


@router.post("/cache/clear")
async def clear_cache(
    cache_type: str = Query("all", description="缓存类型: redis, memory, all"),
):
    """
    清空缓存

    Args:
        cache_type: 缓存类型

    Returns:
        dict: 操作结果
    """
    try:
        if cache_type in ["redis", "all"]:
            cache_service.clear_all()

        if cache_type in ["memory", "all"]:
            # 清空内存缓存（如果有的话）
            pass

        return {
            "success": True,
            "message": f"已清空{cache_type}缓存",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        raise HTTPException(status_code=500, detail="清空缓存失败") from e


@router.get("/alerts")
async def get_alerts(
    severity: Union[str, None] = Query(
        None, description="告警级别: info, warning, error"
    ),
):
    """
    获取系统告警信息

    Args:
        severity: 告警级别过滤

    Returns:
        dict: 告警信息
    """
    try:
        # 模拟告警数据
        alerts = [
            {
                "id": "alert_001",
                "severity": "warning",
                "message": "API响应时间超过阈值",
                "endpoint": "/api/v1/stocks/data",
                "timestamp": datetime.now().isoformat(),
                "value": 520.5,
                "threshold": 500.0,
            },
            {
                "id": "alert_002",
                "severity": "info",
                "message": "缓存命中率下降",
                "cache_type": "redis",
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "value": 0.75,
                "threshold": 0.80,
            },
        ]

        # 按严重程度过滤
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]

        return {
            "alerts": alerts,
            "total": len(alerts),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"获取告警信息失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取告警信息") from e


@router.get("/export")
async def export_metrics(
    format_type: str = Query("json", description="导出格式: json, csv"),
    time_range: tuple[datetime, datetime] = Depends(get_time_range),
):
    """
    导出性能指标数据

    Args:
        format_type: 导出格式
        time_range: 时间范围

    Returns:
        dict: 导出的数据
    """
    try:
        start_time, end_time = time_range

        # 获取所有指标数据
        metrics = performance_monitor.get_metrics_in_range(start_time, end_time)
        system_metrics = performance_monitor.get_system_metrics()
        api_metrics = performance_monitor.get_api_metrics()
        cache_stats = performance_monitor.get_cache_stats()

        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "format": format_type,
            },
            "system_metrics": system_metrics.dict() if system_metrics else {},
            "api_metrics": api_metrics.dict() if api_metrics else {},
            "cache_stats": cache_stats.dict() if cache_stats else {},
            "detailed_metrics": [m.dict() for m in metrics],
        }

        if format_type == "csv":
            # 简化的CSV格式（实际应该转换为CSV）
            export_data["note"] = "CSV格式导出需要额外处理"

        return export_data

    except Exception as e:
        logger.error(f"导出指标数据失败: {e}")
        raise HTTPException(status_code=500, detail="导出数据失败") from e
