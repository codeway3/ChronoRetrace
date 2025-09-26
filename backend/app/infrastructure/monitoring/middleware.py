from __future__ import annotations

# !/usr/bin/env python3
"""
ChronoRetrace - 监控中间件

本模块提供FastAPI应用的监控中间件，自动收集API性能指标、
响应时间统计、错误率监控等功能。

Author: ChronoRetrace Team
Date: 2024
"""


import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    性能监控中间件

    自动收集API请求的性能指标，包括响应时间、成功率等。
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: list | None = None,
        include_request_body: bool = False,
        include_response_body: bool = False,
    ):
        """
        初始化监控中间件

        Args:
            app: ASGI应用
            exclude_paths: 排除监控的路径列表
            include_request_body: 是否包含请求体信息
            include_response_body: 是否包含响应体信息
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并收集性能指标

        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP响应
        """
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)

        # 记录请求开始时间
        start_time = time.time()

        # 提取请求信息
        method = request.method
        endpoint = self._extract_endpoint(request)

        # 初始化响应变量
        response: Response | None = None
        success = True
        status_code = 200

        try:
            # 执行请求
            response = await call_next(request)
            # 确保response不为None并获取status_code
            status_code = response.status_code if response else 500
            success = 200 <= status_code < 400

            # 计算响应时间
            response_time_ms = (time.time() - start_time) * 1000

            # 记录API性能指标
            performance_monitor.record_api_request(
                endpoint=endpoint,
                method=method,
                response_time_ms=response_time_ms,
                success=success,
            )

            # 记录详细指标
            self._record_detailed_metrics(
                request,
                response,
                endpoint,
                method,
                response_time_ms,
                status_code,
                success,
            )

            # 确保response不为None
            if response is None:
                from fastapi import HTTPException

                raise HTTPException(status_code=500, detail="Internal server error")

            return response

        except Exception as e:
            # 处理异常
            success = False
            status_code = 500
            response_time_ms = (time.time() - start_time) * 1000

            logger.error(f"请求处理异常: {endpoint} - {e}")

            # 记录异常情况的指标
            performance_monitor.record_api_request(
                endpoint=endpoint,
                method=method,
                response_time_ms=response_time_ms,
                success=success,
            )

            # 重新抛出异常
            raise

    def _should_exclude_path(self, path: str) -> bool:
        """
        检查路径是否应该被排除

        Args:
            path: 请求路径

        Returns:
            bool: 是否排除
        """
        return any(excluded in path for excluded in self.exclude_paths)

    def _extract_endpoint(self, request: Request) -> str:
        """
        提取API端点

        Args:
            request: HTTP请求

        Returns:
            str: API端点
        """
        # 尝试从路由中获取端点模式
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        # 回退到原始路径，但移除查询参数
        path = request.url.path

        # 简化路径参数（将数字ID替换为占位符）
        import re

        path = re.sub(r"/\d+", "/{id}", path)
        path = re.sub(r"/[a-f0-9-]{36}", "/{uuid}", path)  # UUID

        return path

    def _record_detailed_metrics(
        self,
        request: Request,
        response: Response | None,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        success: bool,
    ):
        """
        记录详细的性能指标

        Args:
            request: HTTP请求
            response: HTTP响应
            endpoint: API端点
            method: HTTP方法
            response_time_ms: 响应时间(毫秒)
            status_code: 状态码
            success: 是否成功
        """
        try:
            # 基础标签
            tags = {
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code),
                "success": str(success),
                "type": "api",
            }

            # 添加用户代理信息
            user_agent = request.headers.get("user-agent", "unknown")
            if "python" in user_agent.lower():
                tags["client_type"] = "api_client"
            elif "mozilla" in user_agent.lower():
                tags["client_type"] = "browser"
            else:
                tags["client_type"] = "other"

            # 记录响应时间分布
            if response_time_ms < 100:
                tags["response_time_bucket"] = "fast"
            elif response_time_ms < 500:
                tags["response_time_bucket"] = "normal"
            elif response_time_ms < 2000:
                tags["response_time_bucket"] = "slow"
            else:
                tags["response_time_bucket"] = "very_slow"

            # 记录请求大小（如果可用）
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    request_size = int(content_length)
                    performance_monitor.record_metric(
                        f"api.{endpoint.replace('/', '_')}.request_size_bytes",
                        request_size,
                        tags,
                    )
                except ValueError:
                    pass

            # 记录响应大小（如果可用）
            if response and hasattr(response, "headers"):
                response_length = response.headers.get("content-length")
                if response_length:
                    try:
                        response_size = int(response_length)
                        performance_monitor.record_metric(
                            f"api.{endpoint.replace('/', '_')}.response_size_bytes",
                            response_size,
                            tags,
                        )
                    except ValueError:
                        pass

            # 记录并发请求数（简化实现）
            performance_monitor.record_metric(
                "api.concurrent_requests", 1, {"type": "api", "endpoint": endpoint}
            )

        except Exception as e:
            logger.error(f"记录详细指标失败: {e}")


class CacheMonitoringMiddleware(BaseHTTPMiddleware):
    """
    缓存监控中间件

    监控缓存相关的HTTP头和响应，自动识别缓存命中情况。
    """

    def __init__(self, app: ASGIApp):
        """
        初始化缓存监控中间件

        Args:
            app: ASGI应用
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并监控缓存使用情况

        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP响应
        """
        # 检查请求中的缓存相关头
        request.headers.get("cache-control", "")
        request.headers.get("if-none-match")
        request.headers.get("if-modified-since")

        # 执行请求
        response = await call_next(request)

        # 分析响应中的缓存信息
        self._analyze_cache_response(request, response)

        return response

    def _analyze_cache_response(self, request: Request, response: Response):
        """
        分析响应中的缓存信息

        Args:
            request: HTTP请求
            response: HTTP响应
        """
        try:
            endpoint = self._extract_endpoint(request)

            # 检查缓存相关的响应头
            cache_control = response.headers.get("cache-control", "")
            etag = response.headers.get("etag")
            last_modified = response.headers.get("last-modified")

            # 检查是否是304 Not Modified响应（缓存命中）
            if response.status_code == 304:
                performance_monitor.record_cache_hit(f"http_cache_{endpoint}")
                performance_monitor.record_metric(
                    "http_cache.hits", 1, {"endpoint": endpoint, "type": "http_cache"}
                )

            # 检查是否设置了缓存头
            if cache_control or etag or last_modified:
                performance_monitor.record_metric(
                    "http_cache.cacheable_responses",
                    1,
                    {"endpoint": endpoint, "type": "http_cache"},
                )

        except Exception as e:
            logger.error(f"分析缓存响应失败: {e}")

    def _extract_endpoint(self, request: Request) -> str:
        """
        提取API端点（复用PerformanceMonitoringMiddleware的方法）
        """
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        path = request.url.path
        import re

        path = re.sub(r"/\d+", "/{id}", path)
        path = re.sub(r"/[a-f0-9-]{36}", "/{uuid}", path)

        return path


def create_monitoring_middleware(
    app: ASGIApp,
    enable_performance: bool = True,
    enable_cache: bool = True,
    exclude_paths: list | None = None,
) -> ASGIApp:
    """
    创建监控中间件的工厂函数

    Args:
        app: ASGI应用
        enable_performance: 是否启用性能监控
        enable_cache: 是否启用缓存监控
        exclude_paths: 排除监控的路径列表

    Returns:
        ASGIApp: 包装了监控中间件的应用
    """
    if enable_cache:
        app = CacheMonitoringMiddleware(app)

    if enable_performance:
        app = PerformanceMonitoringMiddleware(app, exclude_paths=exclude_paths)

    return app
