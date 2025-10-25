#!/usr/bin/env python3
"""
Redis缓存管理器
提供统一的缓存操作接口，包括键管理、过期策略和失效机制
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any, cast

import redis
from redis.exceptions import ConnectionError, TimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheKeyManager:
    """缓存键管理器"""

    # 键前缀定义
    PREFIXES = {
        "stock_info": "stock:info",
        "stock_daily": "stock:daily",
        "stock_metrics": "stock:metrics",
        "filter_result": "filter:result",
        "system_config": "system:config",
        "user_session": "user:session",
        "api_cache": "api:cache",
        "market_metrics": "market:metrics",
        "fundamental_data": "fundamental:data",
    }

    # 默认TTL配置（秒）
    DEFAULT_TTL = {
        "stock_info": 86400,  # 24小时
        "stock_daily": 3600,  # 1小时
        "stock_metrics": 1800,  # 30分钟
        "filter_result": 900,  # 15分钟
        "system_config": 3600,  # 1小时
        "user_session": 7200,  # 2小时
        "api_cache": 900,  # 15分钟
        "market_metrics": 3600,  # 1小时
        "fundamental_data": 7200,  # 2小时
    }

    @classmethod
    def generate_key(
        cls,
        key_type: str,
        identifier: str,
        date_str: str | None = None,
        market: str | None = None,
        version: str = "v1",
    ) -> str:
        """生成标准化的缓存键

        Args:
            key_type: 键类型，必须在PREFIXES中定义
            identifier: 标识符（如股票代码）
            date_str: 日期字符串（可选）
            market: 市场类型（可选）
            version: 版本号（默认v1）

        Returns:
            标准化的缓存键

        Example:
            generate_key('stock_info', '000001.SZ') -> 'stock:info:000001.SZ:v1'
            generate_key('stock_daily', '000001.SZ', '20240115') -> 'stock:daily:000001.SZ:20240115:v1'
        """
        if key_type not in cls.PREFIXES:
            raise ValueError(
                f"Invalid key_type: {key_type}. Must be one of {list(cls.PREFIXES.keys())}"
            )

        parts = [cls.PREFIXES[key_type], identifier]

        if date_str:
            parts.append(date_str)
        if market:
            parts.append(market)

        parts.append(version)

        return ":".join(parts)

    @classmethod
    def generate_pattern(cls, key_type: str, pattern: str = "*") -> str:
        """生成键模式，用于批量操作

        Args:
            key_type: 键类型
            pattern: 匹配模式（默认*）

        Returns:
            键模式字符串
        """
        if key_type not in cls.PREFIXES:
            raise ValueError(f"Invalid key_type: {key_type}")

        return f"{cls.PREFIXES[key_type]}:{pattern}"

    @classmethod
    def get_ttl(cls, key_type: str) -> int:
        """获取指定键类型的默认TTL"""
        return cls.DEFAULT_TTL.get(key_type, 3600)

    @classmethod
    def generate_key_with_hash(
        cls,
        key_type: str,
        identifier: str,
        params: dict[str, Any] | None = None,
        version: str = "v1",
    ) -> str:
        """生成带参数哈希的缓存键

        Args:
            key_type: 键类型
            identifier: 标识符
            params: 参数字典，将被哈希化
            version: 版本号

        Returns:
            带哈希的缓存键
        """
        if key_type not in cls.PREFIXES:
            raise ValueError(
                f"Invalid key_type: {key_type}. Must be one of {list(cls.PREFIXES.keys())}"
            )

        parts = [cls.PREFIXES[key_type], identifier]

        if params:
            # 对参数进行排序并哈希化
            param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
            param_hash = hashlib.sha256(param_str.encode("utf-8")).hexdigest()[:8]
            parts.append(param_hash)

        parts.append(version)

        return ":".join(parts)

    @classmethod
    def parse_key(cls, key: str) -> dict[str, str]:
        """解析缓存键，提取组成部分

        Args:
            key: 缓存键

        Returns:
            包含键组成部分的字典
        """
        parts = key.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid cache key format: {key}")

        result = {
            "prefix": ":".join(parts[:2]),
            "identifier": parts[2],
            "version": parts[-1],
        }

        # 解析可选部分
        if len(parts) > 4:
            if len(parts) == 5:
                result["date_or_market"] = parts[3]
            elif len(parts) == 6:
                result["date"] = parts[3]
                result["market"] = parts[4]

        return result


class RedisCacheManager:
    """Redis缓存管理器"""

    def __init__(self, redis_url: str | None = None):
        """初始化Redis连接

        Args:
            redis_url: Redis连接URL，默认使用配置文件中的设置
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client = None
        self._connection_pool = None
        self.key_manager = CacheKeyManager()

        # 性能统计
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}

    @property
    def redis_client(self) -> redis.Redis:
        """获取Redis客户端实例（懒加载）"""
        if self._redis_client is None:
            try:
                # 创建连接池
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )

                # 创建Redis客户端
                self._redis_client = redis.Redis(
                    connection_pool=self._connection_pool, decode_responses=True
                )

                # 测试连接
                self._redis_client.ping()
                logger.info("Redis connection established successfully")

            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        return self._redis_client

    def _serialize_value(self, value: Any) -> str:
        """序列化值为JSON字符串"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value)
        return json.dumps(value, default=str, ensure_ascii=False)

    def _deserialize_value(self, value: Any) -> Any:
        """反序列化JSON字符串为Python对象"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def _handle_redis_error(self, operation: str, key: str, error: Exception):
        """处理Redis操作错误"""
        self.stats["errors"] += 1
        # 在异常上下文中记录堆栈信息
        logger.exception(
            "Redis %s operation failed for key '%s': %s", operation, key, error
        )

    async def get(self, key: str) -> Any | None:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回None
        """
        try:
            import asyncio

            # 返回类型为 ResponseT（通常为 bytes 或 None），按需交由反序列化处理
            value = await asyncio.to_thread(self.redis_client.get, key)
            if value is not None:
                self.stats["hits"] += 1
                return self._deserialize_value(value)
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            self._handle_redis_error("GET", key, e)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        key_type: str | None = None,
    ) -> bool:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果为None则使用默认TTL
            key_type: 键类型，用于确定默认TTL

        Returns:
            操作是否成功
        """
        try:
            import asyncio

            serialized_value = self._serialize_value(value)

            # 确定TTL
            if ttl is None and key_type:
                ttl = self.key_manager.get_ttl(key_type)

            if ttl:
                result_bool = bool(
                    await asyncio.to_thread(
                        self.redis_client.setex, key, ttl, serialized_value
                    )
                )
            else:
                result_bool = bool(
                    await asyncio.to_thread(
                        self.redis_client.set, key, serialized_value
                    )
                )

            if result_bool:
                self.stats["sets"] += 1
                logger.debug(f"Cache set: {key} (TTL: {ttl})")

            return result_bool
        except Exception as e:
            self._handle_redis_error("SET", key, e)
            return False

    def delete(self, key: str) -> bool:
        """删除缓存

        Args:
            key: 缓存键

        Returns:
            操作是否成功
        """
        try:
            result_int = cast("int", self.redis_client.delete(key))
            if result_int:
                self.stats["deletes"] += 1
                logger.debug(f"Cache deleted: {key}")
            return bool(result_int)
        except Exception as e:
            self._handle_redis_error("DELETE", key, e)
            return False

    async def async_delete(self, key: str) -> bool:
        """异步删除缓存（线程池包装）"""
        try:
            import asyncio

            result_int = await asyncio.to_thread(self.redis_client.delete, key)
            if int(cast("int", result_int)):
                self.stats["deletes"] += 1
                logger.debug(f"Cache deleted: {key}")
            return bool(result_int)
        except Exception as e:
            self._handle_redis_error("DELETE", key, e)
            return False

    def delete_pattern(self, pattern: str) -> int:
        """批量删除匹配模式的缓存

        Args:
            pattern: 键模式

        Returns:
            删除的键数量
        """
        try:
            # decode_responses=True -> keys() returns list[str]
            keys = cast("list[str]", self.redis_client.keys(pattern))
            if keys:
                deleted_count = int(cast("int", self.redis_client.delete(*keys)))
                self.stats["deletes"] += deleted_count
                logger.info(
                    f"Batch deleted {deleted_count} keys matching pattern: {pattern}"
                )
                return deleted_count
            return 0
        except Exception as e:
            self._handle_redis_error("DELETE_PATTERN", pattern, e)
            return 0

    def exists(self, key: str) -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            缓存是否存在
        """
        try:
            return bool(cast("int", self.redis_client.exists(key)))
        except Exception as e:
            self._handle_redis_error("EXISTS", key, e)
            return False

    async def async_exists(self, key: str) -> bool:
        """异步检查缓存是否存在（线程池包装）"""
        try:
            import asyncio

            result = await asyncio.to_thread(self.redis_client.exists, key)
            return bool(cast("int", result))
        except Exception as e:
            self._handle_redis_error("EXISTS", key, e)
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """设置缓存过期时间

        Args:
            key: 缓存键
            ttl: 过期时间（秒）

        Returns:
            操作是否成功
        """
        try:
            result = bool(self.redis_client.expire(key, ttl))
            logger.debug(f"Cache TTL updated: {key} -> {ttl}s")
            return result
        except Exception as e:
            self._handle_redis_error("EXPIRE", key, e)
            return False

    async def async_expire(self, key: str, ttl: int) -> bool:
        """异步设置缓存过期时间（线程池包装）"""
        try:
            import asyncio

            result = await asyncio.to_thread(self.redis_client.expire, key, ttl)
            logger.debug(f"Cache TTL updated: {key} -> {ttl}s")
            return bool(result)
        except Exception as e:
            self._handle_redis_error("EXPIRE", key, e)
            return False

    def get_ttl(self, key: str) -> int:
        """获取缓存剩余过期时间

        Args:
            key: 缓存键

        Returns:
            剩余过期时间（秒），-1表示永不过期，-2表示键不存在
        """
        try:
            # redis-py 类型存根返回 ResponseT，这里显式转换为 int 以满足类型检查
            return int(cast("int", self.redis_client.ttl(key)))
        except Exception as e:
            self._handle_redis_error("TTL", key, e)
            return -2

    def increment(
        self, key: str, amount: int = 1, ttl: int | None = None
    ) -> int | None:
        """原子性递增操作

        Args:
            key: 缓存键
            amount: 递增量（默认1）
            ttl: 过期时间（秒）

        Returns:
            递增后的值
        """
        try:
            # redis-py 类型存根返回 ResponseT，这里显式转换为 int 以满足类型检查
            result = cast("int", self.redis_client.incr(key, amount))
            if ttl:
                ttl_val = int(cast("int", self.redis_client.ttl(key)))
                if ttl_val <= 0:
                    self.redis_client.expire(key, ttl)
            return result
        except Exception as e:
            self._handle_redis_error("INCR", key, e)
            return None

    async def async_increment(
        self, key: str, amount: int = 1, ttl: int | None = None
    ) -> int | None:
        """异步原子性递增操作（线程池包装）"""
        try:
            import asyncio

            result = await asyncio.to_thread(self.redis_client.incr, key, amount)
            if ttl:
                ttl_val = int(
                    cast("int", await asyncio.to_thread(self.redis_client.ttl, key))
                )
                if ttl_val <= 0:
                    await asyncio.to_thread(self.redis_client.expire, key, ttl)
            return cast("int", result)
        except Exception as e:
            self._handle_redis_error("INCR", key, e)
            return None

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            包含统计信息的字典
        """
        total_operations = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_operations * 100) if total_operations > 0 else 0
        )

        try:
            redis_info = cast("dict[str, Any]", self.redis_client.info("memory"))
            clients_info = cast("dict[str, Any]", self.redis_client.info("clients"))
            redis_stats = {
                "used_memory": redis_info.get("used_memory", 0),
                "used_memory_human": redis_info.get("used_memory_human", "0B"),
                "maxmemory": redis_info.get("maxmemory", 0),
                "connected_clients": clients_info.get("connected_clients", 0),
            }
        except Exception:
            redis_stats = {}

        return {
            "cache_stats": self.stats.copy(),
            "hit_rate": round(hit_rate, 2),
            "redis_stats": redis_stats,
            "last_updated": datetime.now().isoformat(),
        }

    def clear_stats(self):
        """清空统计信息"""
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}
        logger.info("Cache statistics cleared")

    def flush_all(self) -> bool:
        """清空所有缓存（谨慎使用）

        Returns:
            操作是否成功
        """
        try:
            result = self.redis_client.flushdb()
            logger.warning("All cache data has been flushed")
            return bool(result)
        except Exception as e:
            logger.exception("Failed to flush cache: %s", e)
            return False

    def ping(self) -> bool:
        """检查Redis连接状态

        Returns:
            连接是否正常
        """
        try:
            return bool(self.redis_client.ping())
        except Exception as e:
            logger.exception("Redis ping failed: %s", e)
            return False

    async def health_check(self) -> bool:
        """Redis健康检查

        Returns:
            健康检查结果
        """
        try:
            # 测试基本连接
            if not self.ping():
                return False

            # 测试基本操作
            test_key = "health_check_test"
            test_value = "test"

            # 设置测试值
            await self.set(test_key, test_value, ttl=10)

            # 获取测试值
            retrieved_value = await self.get(test_key)

            # 删除测试值
            self.delete(test_key)

            return retrieved_value == test_value
        except Exception as e:
            logger.exception("Redis health check failed: %s", e)
            return False

    def get_info(self, section: str = "memory") -> dict[str, Any]:
        """获取Redis信息

        Args:
            section: 信息类型（memory, clients等）

        Returns:
            Redis信息字典
        """
        try:
            return cast("dict[str, Any]", self.redis_client.info(section))
        except Exception as e:
            logger.exception("Failed to get Redis info: %s", e)
            return {}

    def close(self):
        """关闭Redis连接"""
        if self._connection_pool:
            self._connection_pool.disconnect()
            logger.info("Redis connection pool closed")


# 全局缓存管理器实例
cache_manager = RedisCacheManager()


def cache_result(
    key_type: str,
    ttl: int | None = None,
    key_generator: Callable | None = None,
):
    """缓存装饰器

    Args:
        key_type: 缓存键类型
        ttl: 过期时间（秒）
        key_generator: 自定义键生成函数

    Example:
        @cache_result('stock_info', ttl=3600)
        def get_stock_info(stock_code: str):
            return fetch_stock_info(stock_code)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            import hashlib
            import inspect
            import json

            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                # 默认键生成逻辑
                func_name = func.__name__
                args_hash = hashlib.sha256(
                    json.dumps([args, kwargs], default=str, sort_keys=True).encode()
                ).hexdigest()[:8]
                cache_key = cache_manager.key_manager.generate_key(
                    key_type, f"{func_name}_{args_hash}"
                )

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            # 如果历史上错误地缓存了协程对象，删除并视为未命中
            if cached_result is not None and inspect.isawaitable(cached_result):
                await cache_manager.async_delete(cache_key)
                cached_result = None
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result

            # 执行函数并缓存结果（正确处理同步/异步函数）
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            if result is not None and not inspect.isawaitable(result):
                await cache_manager.set(cache_key, result, ttl=ttl, key_type=key_type)
                logger.debug(f"Cache set for {cache_key}")

            return result

        return wrapper

    return decorator


# 创建全局Redis缓存管理器实例
redis_cache_manager = RedisCacheManager()
