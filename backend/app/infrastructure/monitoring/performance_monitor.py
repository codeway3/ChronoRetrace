"""

ChronoRetrace - 性能监控模块

本模块提供系统性能监控、缓存命中率统计、API响应时间追踪等功能。
支持实时监控和历史数据分析，为系统优化提供数据支持。

Author: ChronoRetrace Team
Date: 2024
"""

from __future__ import annotations

# !/usr/bin/env python3
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import TYPE_CHECKING, Any

import psutil

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """
    性能指标数据类
    """

    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""


@dataclass
class CacheStats:
    """
    缓存统计数据类
    """

    cache_name: str
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def update_hit_rate(self):
        """更新命中率"""
        self.total_requests = self.hits + self.misses
        if self.total_requests > 0:
            self.hit_rate = self.hits / self.total_requests
        else:
            self.hit_rate = 0.0
        self.last_updated = datetime.utcnow()


@dataclass
class APIMetrics:
    """
    API性能指标数据类
    """

    endpoint: str
    method: str
    total_requests: int = 0
    success_requests: int = 0
    error_requests: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float("inf")
    max_response_time_ms: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def add_request(self, response_time_ms: float, success: bool = True):
        """添加请求记录"""
        self.total_requests += 1
        if success:
            self.success_requests += 1
        else:
            self.error_requests += 1

        self.response_times.append(response_time_ms)
        self.min_response_time_ms = min(self.min_response_time_ms, response_time_ms)
        self.max_response_time_ms = max(self.max_response_time_ms, response_time_ms)

        # 计算平均响应时间
        if self.response_times:
            self.avg_response_time_ms = sum(self.response_times) / len(
                self.response_times
            )

        self.last_updated = datetime.utcnow()


class PerformanceMonitor:
    """
    性能监控器

    提供系统性能监控、缓存统计、API性能追踪等功能。
    """

    def __init__(self, max_metrics_history: int = 10000):
        """初始化性能监控器"""
        self.max_metrics_history = max_metrics_history
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        self.cache_stats: dict[str, CacheStats] = {}
        self.api_metrics: dict[str, APIMetrics] = {}
        self.system_metrics: dict[str, Any] = {}

        # 线程安全锁
        self._lock = Lock()

        # 监控配置
        # 环境变量开关：ENABLE_SYSTEM_MONITORING = ["1","true","yes"] 开启，否则关闭
        env_val = os.getenv("ENABLE_SYSTEM_MONITORING", "true").strip().lower()
        self.monitoring_enabled = env_val in {"1", "true", "yes", "on"}
        self.collection_interval = 60  # 秒

        # 启动后台监控线程
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        if self.monitoring_enabled:
            self.start_monitoring()
        else:
            logger.info("性能监控未启动：ENABLE_SYSTEM_MONITORING=%s", env_val)

    def start_monitoring(self):
        """
        启动后台监控
        """
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(
                target=self._background_monitoring, daemon=True
            )
            self._monitoring_thread.start()
            logger.info("性能监控已启动")

    def stop_monitoring(self):
        """
        停止后台监控
        """
        self._stop_monitoring.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("性能监控已停止")

    def _background_monitoring(self):
        """
        后台监控线程
        """
        while not self._stop_monitoring.is_set():
            try:
                if self.monitoring_enabled:
                    self._collect_system_metrics()

                # 等待下次收集
                self._stop_monitoring.wait(self.collection_interval)

            except Exception:
                logger.exception("后台监控出错")
                self._stop_monitoring.wait(10)  # 出错后等待10秒

    def _collect_system_metrics(self):
        """
        收集系统性能指标
        """
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric(
                "system.cpu.usage_percent", cpu_percent, {"type": "system"}
            )

            # 内存使用情况
            memory = psutil.virtual_memory()
            self.record_metric(
                "system.memory.usage_percent", memory.percent, {"type": "system"}
            )
            self.record_metric(
                "system.memory.available_mb",
                memory.available / 1024 / 1024,
                {"type": "system"},
            )

            # 磁盘使用情况
            disk = psutil.disk_usage("/")
            self.record_metric(
                "system.disk.usage_percent",
                (disk.used / disk.total) * 100,
                {"type": "system"},
            )

            # 网络IO
            net_io = psutil.net_io_counters()
            self.record_metric(
                "system.network.bytes_sent", net_io.bytes_sent, {"type": "system"}
            )
            self.record_metric(
                "system.network.bytes_recv", net_io.bytes_recv, {"type": "system"}
            )

            # 更新系统指标缓存
            with self._lock:
                self.system_metrics.update(
                    {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "memory_available_mb": memory.available / 1024 / 1024,
                        "disk_usage_percent": (disk.used / disk.total) * 100,
                        "last_updated": datetime.utcnow(),
                    }
                )

        except Exception:
            logger.exception("收集系统指标失败")

    def record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str = "",
        description: str = "",
    ):
        """
        记录性能指标

        Args:
            name: 指标名称
            value: 指标值
            tags: 标签
            unit: 单位
            description: 描述
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            unit=unit,
            description=description,
        )

        with self._lock:
            self.metrics_history.append(metric)

    def record_cache_hit(self, cache_name: str, response_time_ms: float = 0.0):
        """
        记录缓存命中

        Args:
            cache_name: 缓存名称
            response_time_ms: 响应时间(毫秒)
        """
        with self._lock:
            if cache_name not in self.cache_stats:
                self.cache_stats[cache_name] = CacheStats(cache_name=cache_name)

            stats = self.cache_stats[cache_name]
            stats.hits += 1

            # 更新平均响应时间
            if response_time_ms > 0:
                total_time = (
                    stats.avg_response_time_ms * (stats.hits - 1) + response_time_ms
                )
                stats.avg_response_time_ms = total_time / stats.hits

            stats.update_hit_rate()

        # 记录指标
        self.record_metric(
            f"cache.{cache_name}.hits", 1, {"cache_name": cache_name, "type": "cache"}
        )

    def record_cache_miss(self, cache_name: str, response_time_ms: float = 0.0):
        """
        记录缓存未命中

        Args:
            cache_name: 缓存名称
            response_time_ms: 响应时间(毫秒)
        """
        with self._lock:
            if cache_name not in self.cache_stats:
                self.cache_stats[cache_name] = CacheStats(cache_name=cache_name)

            stats = self.cache_stats[cache_name]
            stats.misses += 1

            # 更新平均响应时间（未命中也计入）
            if response_time_ms > 0:
                total_time = (
                    stats.avg_response_time_ms * (stats.misses - 1) + response_time_ms
                )
                stats.avg_response_time_ms = total_time / stats.misses

            stats.update_hit_rate()

        # 记录指标
        self.record_metric(
            f"cache.{cache_name}.misses", 1, {"cache_name": cache_name, "type": "cache"}
        )

    def record_api_request(
        self, endpoint: str, method: str, response_time_ms: float, success: bool = True
    ):
        """
        记录API请求

        Args:
            endpoint: API端点
            method: HTTP方法
            response_time_ms: 响应时间(毫秒)
            success: 是否成功
        """
        key = f"{method}:{endpoint}"

        with self._lock:
            if key not in self.api_metrics:
                self.api_metrics[key] = APIMetrics(endpoint=endpoint, method=method)

            self.api_metrics[key].add_request(response_time_ms, success)

        # 记录指标
        status = "success" if success else "error"
        self.record_metric(
            f"api.{endpoint.replace('/', '_')}.response_time_ms",
            response_time_ms,
            {"endpoint": endpoint, "method": method, "status": status, "type": "api"},
        )

    @contextmanager
    def measure_time(self, operation_name: str, tags: dict[str, str] | None = None):
        """
        测量操作耗时的上下文管理器

        Args:
            operation_name: 操作名称
            tags: 标签
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_metric(
                f"operation.{operation_name}.duration_ms",
                duration_ms,
                tags or {"type": "operation"},
            )

    def get_cache_stats(self, cache_name: str | None = None) -> dict[str, CacheStats]:
        """
        获取缓存统计信息

        Args:
            cache_name: 缓存名称，None表示获取所有缓存统计

        Returns:
            Dict: 缓存统计信息
        """
        with self._lock:
            if cache_name:
                return {
                    cache_name: self.cache_stats.get(cache_name, CacheStats(cache_name))
                }
            return self.cache_stats.copy()

    def get_api_metrics(self, endpoint: str | None = None) -> dict[str, APIMetrics]:
        """
        获取API性能指标

        Args:
            endpoint: API端点，None表示获取所有API指标

        Returns:
            Dict: API性能指标
        """
        with self._lock:
            if endpoint:
                return {k: v for k, v in self.api_metrics.items() if endpoint in k}
            return self.api_metrics.copy()

    def get_system_metrics(self) -> dict[str, Any]:
        """
        获取系统性能指标

        Returns:
            Dict: 系统性能指标
        """
        with self._lock:
            return self.system_metrics.copy()

    def get_metrics_in_range(
        self, start_time: datetime, end_time: datetime
    ) -> list[PerformanceMetric]:
        """按时间范围获取历史指标列表"""
        with self._lock:
            return [
                m for m in self.metrics_history if start_time <= m.timestamp <= end_time
            ]

    def get_metrics_summary(self, time_range_minutes: int = 60) -> dict[str, Any]:
        """
        获取指标摘要

        Args:
            time_range_minutes: 时间范围(分钟)

        Returns:
            Dict: 指标摘要
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_range_minutes)

        with self._lock:
            # 过滤时间范围内的指标
            recent_metrics = [
                m for m in self.metrics_history if m.timestamp >= cutoff_time
            ]

            # 按类型分组统计
            metrics_by_type = defaultdict(list)
            for metric in recent_metrics:
                metric_type = metric.tags.get("type", "unknown")
                metrics_by_type[metric_type].append(metric)

            summary = {
                "time_range_minutes": time_range_minutes,
                "total_metrics": len(recent_metrics),
                # 先占位，稍后填充类型统计
                "metrics_by_type": {},
                "cache_summary": self._get_cache_summary(),
                "api_summary": self._get_api_summary(),
                "system_summary": self.get_system_metrics(),
                "generated_at": datetime.utcnow(),
            }

            # 统计各类型指标（使用强类型字典避免 mypy 将值推断为 object）
            metrics_by_type_summary: dict[str, dict[str, float | int]] = {}
            for metric_type, metrics in metrics_by_type.items():
                metrics_by_type_summary[metric_type] = {
                    "count": len(metrics),
                    "avg_value": (
                        sum(m.value for m in metrics) / len(metrics) if metrics else 0
                    ),
                }
            summary["metrics_by_type"] = metrics_by_type_summary

            return summary

    def _get_cache_summary(self) -> dict[str, Any]:
        """
        获取缓存摘要
        """
        if not self.cache_stats:
            return {"total_caches": 0, "overall_hit_rate": 0.0}

        total_hits = sum(stats.hits for stats in self.cache_stats.values())
        total_requests = sum(
            stats.total_requests for stats in self.cache_stats.values()
        )
        overall_hit_rate = total_hits / total_requests if total_requests > 0 else 0.0

        return {
            "total_caches": len(self.cache_stats),
            "overall_hit_rate": overall_hit_rate,
            "total_hits": total_hits,
            "total_requests": total_requests,
            "best_performing_cache": (
                max(self.cache_stats.values(), key=lambda x: x.hit_rate).cache_name
                if self.cache_stats
                else None
            ),
        }

    def _get_api_summary(self) -> dict[str, Any]:
        """
        获取API摘要
        """
        if not self.api_metrics:
            return {"total_endpoints": 0, "avg_response_time_ms": 0.0}

        total_requests = sum(
            metrics.total_requests for metrics in self.api_metrics.values()
        )
        avg_response_time = (
            sum(
                metrics.avg_response_time_ms * metrics.total_requests
                for metrics in self.api_metrics.values()
            )
            / total_requests
            if total_requests > 0
            else 0.0
        )

        success_rate = (
            sum(metrics.success_requests for metrics in self.api_metrics.values())
            / total_requests
            if total_requests > 0
            else 0.0
        )

        return {
            "total_endpoints": len(self.api_metrics),
            "total_requests": total_requests,
            "avg_response_time_ms": avg_response_time,
            "success_rate": success_rate,
            "slowest_endpoint": (
                max(
                    self.api_metrics.values(), key=lambda x: x.avg_response_time_ms
                ).endpoint
                if self.api_metrics
                else None
            ),
        }

    def reset_stats(self, cache_name: str | None = None, endpoint: str | None = None):
        """
        重置统计信息

        Args:
            cache_name: 要重置的缓存名称，None表示重置所有缓存统计
            endpoint: 要重置的API端点，None表示重置所有API统计
        """
        with self._lock:
            if cache_name:
                if cache_name in self.cache_stats:
                    self.cache_stats[cache_name] = CacheStats(cache_name=cache_name)
            elif cache_name is None:
                self.cache_stats.clear()

            if endpoint:
                keys_to_remove = [k for k in self.api_metrics if endpoint in k]
                for key in keys_to_remove:
                    del self.api_metrics[key]
            elif endpoint is None and cache_name is None:
                self.api_metrics.clear()
                self.metrics_history.clear()

        logger.info(f"统计信息已重置: cache={cache_name}, endpoint={endpoint}")

    def export_metrics(self, format_type: str = "json") -> str:
        """
        导出指标数据

        Args:
            format_type: 导出格式 (json, csv)

        Returns:
            str: 导出的数据
        """
        summary = self.get_metrics_summary()

        if format_type.lower() == "json":
            return json.dumps(summary, indent=2, default=str)
        elif format_type.lower() == "csv":
            # 简化的CSV导出
            lines = ["metric_name,value,timestamp,type"]
            with self._lock:
                for metric in list(self.metrics_history)[-1000:]:  # 最近1000条
                    metric_type = metric.tags.get("type", "unknown")
                    lines.append(
                        f"{metric.name},{metric.value},{metric.timestamp},{metric_type}"
                    )
            return "\n".join(lines)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()


# 装饰器函数
def monitor_performance(
    operation_name: str | None = None, tags: dict[str, str] | None = None
):
    """
    性能监控装饰器

    Args:
        operation_name: 操作名称
        tags: 标签
    """

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            with performance_monitor.measure_time(op_name, tags):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def monitor_cache_operation(cache_name: str):
    """
    缓存操作监控装饰器

    Args:
        cache_name: 缓存名称
    """

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                response_time_ms = (time.time() - start_time) * 1000

                # 根据返回结果判断是否命中
                if result is not None:
                    performance_monitor.record_cache_hit(cache_name, response_time_ms)
                else:
                    performance_monitor.record_cache_miss(cache_name, response_time_ms)
            except Exception:
                response_time_ms = (time.time() - start_time) * 1000
                performance_monitor.record_cache_miss(cache_name, response_time_ms)
                raise
            else:
                return result

        return wrapper

    return decorator
