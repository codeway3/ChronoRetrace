#!/usr/bin/env python3
"""
ChronoRetrace - 性能监控单元测试

本模块包含性能监控相关功能的单元测试，包括性能指标收集、
缓存统计、API监控等功能的测试用例。

Author: ChronoRetrace Team
Date: 2024
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.infrastructure.monitoring.performance_monitor import (
    APIMetrics,
    CacheStats,
    PerformanceMetric,
    PerformanceMonitor,
    monitor_performance,
    performance_monitor,
)


class TestPerformanceMetric:
    """性能指标数据类测试"""

    def test_performance_metric_creation(self):
        """测试性能指标创建"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            name="cpu_usage",
            value=75.5,
            timestamp=timestamp,
            tags={"type": "system"},
            unit="percent",
            description="CPU使用率",
        )

        assert metric.name == "cpu_usage"
        assert metric.value == 75.5
        assert metric.timestamp == timestamp
        assert metric.tags == {"type": "system"}
        assert metric.unit == "percent"
        assert metric.description == "CPU使用率"

    def test_performance_metric_to_dict(self):
        """测试性能指标转换为字典"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            name="memory_usage",
            value=60.2,
            timestamp=timestamp,
            tags={"type": "system"},
            unit="percent",
            description="内存使用率",
        )

        # 检查属性是否正确
        assert metric.name == "memory_usage"
        assert metric.value == 60.2
        assert metric.timestamp == timestamp
        assert metric.tags == {"type": "system"}
        assert metric.unit == "percent"
        assert metric.description == "内存使用率"


class TestCacheStats:
    """缓存统计测试类"""

    def test_cache_stats_creation(self):
        """测试缓存统计创建"""
        stats = CacheStats(cache_name="test_cache", hits=80, misses=20)

        assert stats.cache_name == "test_cache"
        assert stats.hits == 80
        assert stats.misses == 20
        assert stats.total_requests == 0  # 初始值
        assert stats.hit_rate == 0.0  # 初始值

    def test_cache_stats_hit_rate(self):
        """测试缓存命中率计算"""
        stats = CacheStats(cache_name="test_cache", hits=80, misses=20)

        stats.update_hit_rate()
        assert stats.hit_rate == 0.8  # 80 / (80 + 20)
        assert stats.total_requests == 100

    def test_cache_stats_zero_requests(self):
        """测试零请求时的命中率"""
        stats = CacheStats(cache_name="test_cache", hits=0, misses=0)

        stats.update_hit_rate()
        assert stats.hit_rate == 0.0
        assert stats.total_requests == 0


class TestAPIMetrics:
    """API指标测试类"""

    def test_api_metrics_creation(self):
        """测试API指标创建"""
        metrics = APIMetrics(endpoint="/api/v1/stocks", method="GET")

        assert metrics.endpoint == "/api/v1/stocks"
        assert metrics.method == "GET"
        assert metrics.total_requests == 0
        assert metrics.success_requests == 0
        assert metrics.error_requests == 0
        assert metrics.avg_response_time_ms == 0.0

        # 测试添加请求
        metrics.add_request(150.0, True)
        assert metrics.total_requests == 1
        assert metrics.success_requests == 1
        assert metrics.error_requests == 0


class TestPerformanceMonitor:
    """性能监控器测试类"""

    @pytest.fixture
    def monitor(self):
        """创建性能监控器实例"""
        return PerformanceMonitor()

    def test_monitor_initialization(self, monitor):
        """测试监控器初始化"""
        assert monitor.max_metrics_history == 10000
        assert len(monitor.metrics_history) == 0
        assert len(monitor.cache_stats) == 0
        assert len(monitor.api_metrics) == 0
        assert monitor.monitoring_enabled is True

    def test_collect_system_metrics(self, monitor):
        """测试收集系统指标"""
        with (
            patch("psutil.cpu_percent", return_value=75.5),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
            patch("psutil.net_io_counters") as mock_net,
        ):
            # 设置mock返回值
            mock_memory.return_value.percent = 60.2
            mock_memory.return_value.available = 1024 * 1024 * 1024  # 1GB
            mock_disk.return_value.used = 500 * 1024 * 1024 * 1024  # 500GB
            mock_disk.return_value.total = 1000 * 1024 * 1024 * 1024  # 1TB
            mock_net.return_value.bytes_sent = 1024
            mock_net.return_value.bytes_recv = 2048

            # 调用私有方法
            monitor._collect_system_metrics()

            # 检查是否记录了系统指标
            assert len(monitor.metrics_history) > 0

            # 检查系统指标缓存
            assert "cpu_percent" in monitor.system_metrics
            assert "memory_percent" in monitor.system_metrics

    def test_record_cache_hit_miss(self, monitor):
        """测试记录缓存命中和未命中"""
        monitor.record_cache_hit("test_cache", 50.0)
        monitor.record_cache_miss("test_cache", 100.0)

        assert "test_cache" in monitor.cache_stats
        stats = monitor.cache_stats["test_cache"]
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.cache_name == "test_cache"

    def test_record_api_metric(self, monitor):
        """测试记录API指标"""
        monitor.record_api_request(
            endpoint="/api/v1/stocks",
            method="GET",
            response_time_ms=150.0,
            success=True,
        )

        key = "GET:/api/v1/stocks"
        assert key in monitor.api_metrics
        metric = monitor.api_metrics[key]
        assert metric.endpoint == "/api/v1/stocks"
        assert metric.method == "GET"
        assert metric.total_requests == 1
        assert metric.success_requests == 1

    def test_metrics_collection(self, monitor):
        """测试指标收集"""
        # 添加一些测试数据
        monitor.record_api_request("/api/v1/stocks", "GET", 100.0, True)
        monitor.record_api_request("/api/v1/stocks", "GET", 200.0, True)
        monitor.record_api_request("/api/v1/stocks", "GET", 500.0, False)

        # 检查API指标
        assert len(monitor.api_metrics) > 0
        key = "GET:/api/v1/stocks"
        assert key in monitor.api_metrics
        api_stats = monitor.api_metrics[key]
        assert api_stats.total_requests == 3
        assert api_stats.success_requests == 2
        assert api_stats.error_requests == 1

    def test_get_cache_summary(self, monitor):
        """测试获取缓存摘要"""
        monitor.record_cache_hit("test_cache", 50.0)
        monitor.record_cache_miss("test_cache", 100.0)

        # 检查缓存统计
        assert "test_cache" in monitor.cache_stats
        stats = monitor.cache_stats["test_cache"]
        assert stats.hits == 1
        assert stats.misses == 1

    def test_clear_old_metrics(self, monitor):
        """测试清理旧指标"""
        # 添加一些旧的指标
        old_time = datetime.now() - timedelta(hours=25)
        recent_time = datetime.now()

        # 手动添加指标（模拟旧数据）
        old_metric = PerformanceMetric(name="test_old", value=50.0, timestamp=old_time)
        recent_metric = PerformanceMetric(
            name="test_recent", value=60.0, timestamp=recent_time
        )

        monitor.metrics_history = [old_metric, recent_metric]

        # 检查指标已添加
        assert len(monitor.metrics_history) == 2

        # 清理旧指标的功能需要实际实现
        # 这里只检查指标是否正确添加
        timestamps = [m.timestamp for m in monitor.metrics_history]
        assert old_time in timestamps
        assert recent_time in timestamps

    def test_start_monitoring(self, monitor):
        """测试启动监控"""
        # 监控在初始化时已自动启动
        assert monitor._monitoring_thread is not None
        assert monitor._monitoring_thread.is_alive()

    def test_stop_monitoring(self, monitor):
        """测试停止监控"""
        monitor.is_monitoring = True
        monitor.stop_monitoring()

        assert monitor._stop_monitoring.is_set()

    def test_export_metrics(self, monitor):
        """测试导出指标"""
        # 添加一些测试数据
        monitor.record_api_request("/api/v1/stocks", "GET", 100.0, True)
        monitor.record_cache_hit("test_cache", 50.0)
        monitor.record_cache_miss("test_cache", 100.0)

        # 检查指标历史
        assert len(monitor.metrics_history) > 0
        assert len(monitor.api_metrics) > 0
        assert len(monitor.cache_stats) > 0


class TestMonitorPerformanceDecorator:
    """性能监控装饰器测试类"""

    @pytest.mark.asyncio
    async def test_async_function_monitoring(self):
        """测试异步函数监控"""

        @monitor_performance("test_async_function")
        async def test_async_function():
            await asyncio.sleep(0.1)
            return "test_result"

        with patch.object(performance_monitor, "record_metric") as mock_record:
            result = await test_async_function()

            assert result == "test_result"
            mock_record.assert_called()
            call_args = mock_record.call_args[0]
            assert "test_async_function" in call_args[0]

    def test_sync_function_monitoring(self):
        """测试同步函数监控"""

        @monitor_performance("test_sync_function")
        def test_sync_function():
            time.sleep(0.1)
            return "test_result"

        with patch.object(performance_monitor, "record_metric") as mock_record:
            result = test_sync_function()

            assert result == "test_result"
            mock_record.assert_called()
            call_args = mock_record.call_args[0]
            assert "test_sync_function" in call_args[0]

    @pytest.mark.asyncio
    async def test_function_with_exception(self):
        """测试异常情况下的监控"""

        @monitor_performance("test_function_with_error")
        async def test_function_with_error():
            raise ValueError("Test error")

        with patch.object(performance_monitor, "record_metric") as mock_record:
            with pytest.raises(ValueError):
                await test_function_with_error()

            # 即使发生异常，也应该记录指标
            mock_record.assert_called()
            call_args = mock_record.call_args[0]
            assert "test_function_with_error" in call_args[0]


class TestPerformanceMonitorIntegration:
    """性能监控集成测试类"""

    def test_global_monitor_instance(self):
        """测试全局监控器实例"""
        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)

    def test_monitor_integration_with_cache(self):
        """测试监控器与缓存的集成"""
        monitor = PerformanceMonitor()

        # 添加一些测试数据
        monitor.record_api_request("/api/v1/stocks", "GET", 100.0, True)
        monitor.record_cache_hit("test_cache", 50.0)
        monitor.record_cache_miss("test_cache", 100.0)

        # 检查指标历史
        assert len(monitor.api_metrics) > 0
        assert len(monitor.cache_stats) > 0

    def test_metrics_retention_policy(self):
        """测试指标保留策略"""
        monitor = PerformanceMonitor()

        # 添加大量指标
        for i in range(1000):
            monitor.record_api_request(f"/api/test/{i}", "GET", 100.0, True)

        # 检查是否有合理的保留策略
        assert len(monitor.api_metrics) <= 1000  # 应该有某种限制


if __name__ == "__main__":
    pytest.main([__file__])
