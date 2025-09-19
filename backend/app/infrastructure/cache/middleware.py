from typing import Union

# !/usr/bin/env python3
"""
缓存中间件
为FastAPI应用提供缓存功能集成
"""

import hashlib
import logging
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .cache_service import cache_service

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """缓存中间件

    为HTTP请求提供自动缓存功能
    """

    def __init__(self, app, cache_config: Union[dict[str, Any], None] = None):
        """初始化缓存中间件

        Args:
            app: FastAPI应用实例
            cache_config: 缓存配置
        """
        super().__init__(app)
        self.cache_config = cache_config or {}

        # 默认缓存配置
        self.default_config = {
            "enabled": True,
            "default_ttl": 300,  # 5分钟
            "cache_methods": ["GET"],
            "exclude_paths": ["/health", "/metrics", "/docs", "/openapi.json"],
            "include_query_params": True,
            "cache_headers": True,
            "max_response_size": 1024 * 1024,  # 1MB
        }

        # 合并配置
        self.config = {**self.default_config, **self.cache_config}

        # 路径特定配置
        self.path_configs = self.cache_config.get("path_configs", {})

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理HTTP请求

        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器

        Returns:
            HTTP响应
        """
        # 检查是否启用缓存
        if not self.config["enabled"]:
            return await call_next(request)

        # 检查请求方法
        if request.method not in self.config["cache_methods"]:
            return await call_next(request)

        # 检查排除路径
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # 获取路径特定配置
        path_config = self._get_path_config(request.url.path)

        # 生成缓存键
        cache_key = self._generate_cache_key(request)

        # 尝试从缓存获取响应
        start_time = time.time()
        cached_response = await cache_service.redis_cache.get(cache_key)
        cache_lookup_time = time.time() - start_time

        if cached_response is not None:
            logger.debug(
                f"Cache hit for {request.url.path}, lookup time: {cache_lookup_time:.3f}s"
            )

            # 添加缓存头
            response = JSONResponse(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=cached_response.get("headers", {}),
            )
            response.headers["X-Cache-Status"] = "HIT"
            response.headers["X-Cache-Key"] = cache_key
            response.headers["X-Cache-Lookup-Time"] = f"{cache_lookup_time:.3f}s"

            return response

        # 缓存未命中，执行请求
        logger.debug(f"Cache miss for {request.url.path}")

        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time

        # 检查是否应该缓存响应
        if self._should_cache_response(response, path_config):
            await self._cache_response(
                cache_key, response, path_config, processing_time
            )

        # 添加缓存头
        response.headers["X-Cache-Status"] = "MISS"
        response.headers["X-Cache-Key"] = cache_key
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"

        return response

    def _is_excluded_path(self, path: str) -> bool:
        """检查路径是否被排除

        Args:
            path: 请求路径

        Returns:
            是否被排除
        """
        for excluded_path in self.config["exclude_paths"]:
            if path.startswith(excluded_path):
                return True
        return False

    def _get_path_config(self, path: str) -> dict[str, Any]:
        """获取路径特定配置

        Args:
            path: 请求路径

        Returns:
            路径配置
        """
        for pattern, config in self.path_configs.items():
            if path.startswith(pattern):
                return {**self.config, **config}
        return self.config

    def _generate_cache_key(self, request: Request) -> str:
        """生成缓存键

        Args:
            request: HTTP请求

        Returns:
            缓存键
        """
        # 基础键组件
        key_components = [request.method, request.url.path]

        # 包含查询参数
        if self.config["include_query_params"] and request.url.query:
            # 对查询参数进行排序以确保一致性
            sorted_params = sorted(request.query_params.items())
            query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
            key_components.append(query_string)

        # 包含相关头信息
        if self.config["cache_headers"]:
            relevant_headers = ["accept", "accept-language", "authorization"]
            for header in relevant_headers:
                if header in request.headers:
                    key_components.append(f"{header}:{request.headers[header]}")

        # 生成哈希
        key_string = "|".join(key_components)
        cache_key = hashlib.md5(key_string.encode()).hexdigest()

        return f"http_cache:{cache_key}"

    def _should_cache_response(
        self, response: Response, config: dict[str, Any]
    ) -> bool:
        """检查是否应该缓存响应

        Args:
            response: HTTP响应
            config: 缓存配置

        Returns:
            是否应该缓存
        """
        # 检查状态码
        if response.status_code != 200:
            return False

        # 检查响应大小
        if hasattr(response, "body"):
            body_size = len(response.body) if response.body else 0
            if body_size > config["max_response_size"]:
                logger.warning(f"Response too large to cache: {body_size} bytes")
                return False

        # 检查缓存控制头
        cache_control = response.headers.get("cache-control", "")
        if "no-cache" in cache_control or "no-store" in cache_control:
            return False

        return True

    async def _cache_response(
        self,
        cache_key: str,
        response: Response,
        config: dict[str, Any],
        processing_time: float,
    ):
        """缓存响应

        Args:
            cache_key: 缓存键
            response: HTTP响应
            config: 缓存配置
            processing_time: 处理时间
        """
        try:
            # 准备缓存数据
            cache_data = {
                "content": None,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "cached_at": time.time(),
                "processing_time": processing_time,
            }

            # 获取响应内容
            if hasattr(response, "body") and response.body:
                # 对于JSONResponse等
                import json

                try:
                    cache_data["content"] = json.loads(response.body.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    cache_data["content"] = response.body.decode(
                        "utf-8", errors="ignore"
                    )
            elif hasattr(response, "content"):
                cache_data["content"] = response.content

            # 设置TTL
            ttl = config.get("ttl", config["default_ttl"])

            # 缓存响应
            success = cache_service.redis_cache.set(cache_key, cache_data, ttl=ttl)

            if success:
                logger.debug(f"Cached response for key: {cache_key}, TTL: {ttl}s")
            else:
                logger.warning(f"Failed to cache response for key: {cache_key}")

        except Exception as e:
            logger.error(f"Error caching response: {e}")


class CacheInvalidationMiddleware(BaseHTTPMiddleware):
    """缓存失效中间件

    在数据更新时自动失效相关缓存
    """

    def __init__(self, app, invalidation_config: Union[dict[str, Any], None] = None):
        """初始化缓存失效中间件

        Args:
            app: FastAPI应用实例
            invalidation_config: 失效配置
        """
        super().__init__(app)
        self.invalidation_config = invalidation_config or {}

        # 默认失效规则
        self.default_rules = {
            "POST": ["create", "add", "insert"],
            "PUT": ["update", "modify", "edit"],
            "PATCH": ["update", "modify", "patch"],
            "DELETE": ["delete", "remove"],
        }

        # 合并配置
        self.rules = {**self.default_rules, **self.invalidation_config.get("rules", {})}

        # 路径到缓存模式的映射
        self.path_patterns = self.invalidation_config.get(
            "path_patterns",
            {
                "/api/v1/stocks": ["stock_*", "filter_result:*"],
                "/api/v1/metrics": ["stock_metrics:*", "stock_daily:*"],
                "/api/v1/sync": ["stock_*"],
            },
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理HTTP请求

        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器

        Returns:
            HTTP响应
        """
        # 执行请求
        response = await call_next(request)

        # 检查是否需要失效缓存
        if self._should_invalidate_cache(request, response):
            await self._invalidate_cache(request, response)

        return response

    def _should_invalidate_cache(self, request: Request, response: Response) -> bool:
        """检查是否应该失效缓存

        Args:
            request: HTTP请求
            response: HTTP响应

        Returns:
            是否应该失效缓存
        """
        # 检查响应状态
        if response.status_code not in [200, 201, 204]:
            return False

        # 检查请求方法
        if request.method not in self.rules:
            return False

        # 检查路径关键词
        path = request.url.path.lower()
        method_keywords = self.rules[request.method]

        for keyword in method_keywords:
            if keyword in path:
                return True

        return False

    async def _invalidate_cache(self, request: Request, response: Response):
        """失效相关缓存

        Args:
            request: HTTP请求
            response: HTTP响应
        """
        try:
            path = request.url.path

            # 查找匹配的缓存模式
            patterns_to_invalidate = []

            for path_pattern, cache_patterns in self.path_patterns.items():
                if path.startswith(path_pattern):
                    patterns_to_invalidate.extend(cache_patterns)

            # 执行缓存失效
            total_invalidated = 0
            for pattern in patterns_to_invalidate:
                try:
                    count = cache_service.redis_cache.delete_pattern(pattern)
                    total_invalidated += count
                    logger.debug(
                        f"Invalidated {count} cache entries for pattern: {pattern}"
                    )
                except Exception as e:
                    logger.error(f"Error invalidating cache pattern {pattern}: {e}")

            # 失效HTTP缓存
            http_cache_pattern = "http_cache:*"
            try:
                http_count = cache_service.redis_cache.delete_pattern(
                    http_cache_pattern
                )
                total_invalidated += http_count
                logger.debug(f"Invalidated {http_count} HTTP cache entries")
            except Exception as e:
                logger.error(f"Error invalidating HTTP cache: {e}")

            if total_invalidated > 0:
                logger.info(
                    f"Cache invalidation completed for {path}: {total_invalidated} entries"
                )

        except Exception as e:
            logger.error(f"Error in cache invalidation: {e}")


def create_cache_middleware(cache_config: Union[dict[str, Any], None] = None):
    """创建缓存中间件实例

    Args:
        cache_config: 缓存配置

    Returns:
        缓存中间件工厂函数
    """
    return lambda app: CacheMiddleware(app, cache_config)


def create_invalidation_middleware(
    invalidation_config: Union[dict[str, Any], None] = None,
):
    """创建缓存失效中间件实例

    Args:
        invalidation_config: 失效配置

    Returns:
        缓存失效中间件工厂函数
    """
    return lambda app: CacheInvalidationMiddleware(app, invalidation_config)
