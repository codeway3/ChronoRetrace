"""

ChronoRetrace - 监控API端点

本模块提供系统性能监控、缓存统计、API性能等数据的查询接口。
包含实时指标、历史数据、健康检查等功能。

Author: ChronoRetrace Team
Date: 2024
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
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
            cache_service.redis_cache.ping()
        except Exception:
            cache_status = "unhealthy"

        # 数据库状态检查 - 简化实现
        database_status = "healthy"  # 实际应该检查数据库连接

        # 分析问题
        issues = []
        memory_usage_mb = system_metrics.get("memory_available_mb", 0)
        cpu_usage_percent = system_metrics.get("cpu_percent", 0)

        # 计算内存使用量 - 从可用内存推算
        if memory_usage_mb < MEMORY_AVAILABLE_MIN_MB:  # 可用内存少于500MB
            issues.append("内存使用量过高")
        if cpu_usage_percent > CPU_USAGE_HIGH_THRESHOLD:
            issues.append("CPU使用率过高")
        if cache_status == "unhealthy":
            issues.append("缓存服务不可用")
        if database_status == "unhealthy":
            issues.append("数据库连接异常")

        # 确定整体状态
        if issues:
            status = "warning" if len(issues) <= MAX_WARN_ISSUE_COUNT else "critical"
        else:
            status = "healthy"

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
        logger.exception("获取系统健康状态失败")
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

        # 获取API指标(字典: key -> APIMetrics)
        api_metrics = performance_monitor.get_api_metrics()
        metrics_values = list(api_metrics.values())

        # 聚合统计数据
        total_requests = sum(m.total_requests for m in metrics_values)
        avg_response_time = (
            sum(m.avg_response_time_ms * m.total_requests for m in metrics_values)
            / total_requests
            if total_requests > 0
            else 0.0
        )
        success_count = sum(m.success_requests for m in metrics_values)
        error_count = sum(m.error_requests for m in metrics_values)
        success_rate = (success_count / total_requests) if total_requests > 0 else 0.0
        error_rate = (error_count / total_requests) if total_requests > 0 else 0.0

        # 计算RPS(每秒请求数)  # noqa: ERA001
        time_diff_seconds = (end_time - start_time).total_seconds()
        requests_per_second = (
            total_requests / time_diff_seconds if time_diff_seconds > 0 else 0.0
        )

        # 最慢端点: 按平均响应时间降序取前3  # noqa: ERA001
        slowest = sorted(
            metrics_values, key=lambda m: m.avg_response_time_ms, reverse=True
        )[:3]
        slowest_endpoints = [
            {
                "endpoint": m.endpoint,
                "avg_time_ms": round(m.avg_response_time_ms, 2),
                "requests": m.total_requests,
            }
            for m in slowest
        ]

        # 最活跃端点: 按请求总数降序取前3  # noqa: ERA001
        most_active = sorted(
            metrics_values, key=lambda m: m.total_requests, reverse=True
        )[:3]
        most_active_endpoints = [
            {
                "endpoint": m.endpoint,
                "requests": m.total_requests,
                "avg_time_ms": round(m.avg_response_time_ms, 2),
            }
            for m in most_active
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
        logger.exception("获取性能统计失败")
        raise HTTPException(status_code=500, detail="无法获取性能统计") from e


@router.get("/cache", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    获取缓存统计数据

    Returns:
        CacheStatsResponse: 缓存统计数据
    """
    try:
        # 获取缓存统计(字典: cache_name -> CacheStats)
        cache_stats_dict = performance_monitor.get_cache_stats()

        # 获取Redis统计(来自 CacheService.get_cache_info 返回结构)
        redis_info = cache_service.get_cache_info()
        redis_stats = {
            "connected": redis_info.get("connected", False),
            "total_keys": redis_info.get("total_keys", 0),
            "memory_usage_mb": redis_info.get("memory_usage_mb", 0.0),
            "hit_rate": redis_info.get("hit_rate", 0.0),
            "operations_per_second": redis_info.get("ops_per_sec", 0),
        }

        # 内存缓存统计(暂以占位数据, 后续可接入真实内存缓存统计)  # noqa: ERA001
        memory_cache_stats = {
            "size_mb": 45.2,
            "entries": 1250,
            "hit_rate": 0.85,
            "evictions": 23,
        }

        # 计算总体命中率和总操作数
        total_hits = sum(s.hits for s in cache_stats_dict.values())
        total_operations = sum(s.total_requests for s in cache_stats_dict.values())
        overall_hit_rate = (
            total_hits / total_operations if total_operations > 0 else 0.0
        )

        # 热门缓存键(占位数据)  # noqa: ERA001
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
        logger.exception("获取缓存统计失败")
        raise HTTPException(status_code=500, detail="无法获取缓存统计数据") from e


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    metric_type: str | None = Query(None, description="指标类型过滤"),
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
        metrics = performance_monitor.get_metrics_in_range(
            start_time=start_time, end_time=end_time
        )

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
        logger.exception("获取指标数据失败")
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
            # 清空内存缓存(如果有的话)  # noqa: ERA001
            pass

        return {
            "success": True,
            "message": f"已清空{cache_type}缓存",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("清空缓存失败")
        raise HTTPException(status_code=500, detail="清空缓存失败") from e


@router.get("/alerts")
async def get_alerts(
    severity: str | None = Query(None, description="告警级别: info, warning, error"),
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
        logger.exception("获取告警信息失败")
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
        metrics = performance_monitor.get_metrics_in_range(
            start_time=start_time, end_time=end_time
        )
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
            "system_metrics": system_metrics or {},
            "api_metrics": {k: asdict(v) for k, v in api_metrics.items()},
            "cache_stats": {k: asdict(v) for k, v in cache_stats.items()},
            "detailed_metrics": [asdict(m) for m in metrics],
        }

        if format_type == "csv":
            # 简化的CSV格式(实际应该转换为CSV)  # noqa: ERA001
            export_data["note"] = "CSV格式导出需要额外处理"
            return export_data
        else:
            return export_data

    except Exception as e:
        logger.exception("导出指标数据失败")
        raise HTTPException(status_code=500, detail="导出数据失败") from e


@router.get("/prom_metrics")
async def export_prometheus_metrics():
    """
    Prometheus 文本暴露端点，将 PerformanceMonitor 内部指标映射到 Prometheus registry。
    - Counter: api_requests_total{method,endpoint,status}
    - Histogram: api_response_time_seconds{method,endpoint}
    - Gauge: system_cpu_usage_percent, system_memory_usage_percent, system_memory_available_mb, system_disk_usage_percent
    - Gauge: api_concurrent_requests
    """
    try:
        registry = CollectorRegistry()

        # Counters for API requests
        api_requests_total = Counter(
            "api_requests_total",
            "Total API requests grouped by method/endpoint/status",
            ["method", "endpoint", "status"],
            registry=registry,
        )

        # Histogram for API response times (seconds)
        api_response_time_seconds = Histogram(
            "api_response_time_seconds",
            "API response time in seconds",
            ["method", "endpoint"],
            registry=registry,
        )

        # System gauges
        system_cpu_usage_percent = Gauge(
            "system_cpu_usage_percent",
            "System CPU usage percent",
            registry=registry,
        )
        system_memory_usage_percent = Gauge(
            "system_memory_usage_percent",
            "System memory usage percent",
            registry=registry,
        )
        system_memory_available_mb = Gauge(
            "system_memory_available_mb",
            "System memory available in MB",
            registry=registry,
        )
        system_disk_usage_percent = Gauge(
            "system_disk_usage_percent",
            "System disk usage percent",
            registry=registry,
        )

        # Concurrent requests gauge
        api_concurrent_requests = Gauge(
            "api_concurrent_requests",
            "Current number of concurrent API requests",
            registry=registry,
        )

        # Populate API counters and histograms from PerformanceMonitor
        api_metrics = performance_monitor.get_api_metrics()
        for _key, m in api_metrics.items():
            # Counters
            api_requests_total.labels(m.method, m.endpoint, "success").inc(
                m.success_requests
            )
            api_requests_total.labels(m.method, m.endpoint, "error").inc(
                m.error_requests
            )

            # Histogram observations from recorded response times (ms -> seconds)
            for rt_ms in list(m.response_times):
                api_response_time_seconds.labels(m.method, m.endpoint).observe(
                    rt_ms / 1000.0
                )

        # Populate system gauges
        sys = performance_monitor.get_system_metrics()
        if sys:
            cpu = float(sys.get("cpu_percent", 0))
            mem_pct = float(sys.get("memory_percent", 0))
            mem_avail_mb = float(sys.get("memory_available_mb", 0))
            disk_pct = float(sys.get("disk_usage_percent", 0))
            system_cpu_usage_percent.set(cpu)
            system_memory_usage_percent.set(mem_pct)
            system_memory_available_mb.set(mem_avail_mb)
            system_disk_usage_percent.set(disk_pct)

        # Concurrent requests gauge from latest metric history
        latest_concurrent = None
        # get last metric named 'api.concurrent_requests'
        try:
            metrics_list = list(performance_monitor.metrics_history)
            for metric in reversed(metrics_list):
                if metric.name == "api.concurrent_requests":
                    latest_concurrent = float(metric.value)
                    break
        except Exception:
            latest_concurrent = None
        if latest_concurrent is not None:
            api_concurrent_requests.set(latest_concurrent)

        # Return Prometheus exposition
        data = generate_latest(registry)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    except Exception:
        logger.exception("导出 Prometheus 指标失败")
        raise HTTPException(status_code=500, detail="无法导出 Prometheus 指标")


MEMORY_AVAILABLE_MIN_MB = 500
CPU_USAGE_HIGH_THRESHOLD = 80
MAX_WARN_ISSUE_COUNT = 2
