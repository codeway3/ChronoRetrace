#!/usr/bin/env python3
"""
统一缓存服务接口
整合Redis缓存和内存缓存，提供简单易用的缓存API
"""

import logging
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

from .memory_cache import LRUMemoryCache, MultiLevelCache
from .redis_manager import CacheKeyManager, RedisCacheManager

logger = logging.getLogger(__name__)


class CacheService:
    """统一缓存服务

    提供高级缓存操作接口，自动选择合适的缓存策略
    """

    def __init__(self):
        """初始化缓存服务"""
        # 初始化各级缓存
        self.redis_cache = RedisCacheManager()
        self.memory_cache = LRUMemoryCache(max_size=1000, default_ttl=300)
        self.multi_cache = MultiLevelCache(self.memory_cache, self.redis_cache)
        self.key_manager = CacheKeyManager()

        # 初始化统计计数器
        self.hit_count = 0
        self.miss_count = 0

        # 缓存策略配置
        self.cache_strategies = {
            # 股票基本信息 - 使用多级缓存，长TTL
            "stock_info": {
                "use_multi_level": True,
                "redis_ttl": 86400,  # 24小时
                "memory_ttl": 3600,  # 1小时
                "preload": True,
            },
            # 股票日线数据 - 使用Redis缓存，中等TTL
            "stock_daily": {
                "use_multi_level": False,
                "redis_ttl": 3600,  # 1小时
                "memory_ttl": 900,  # 15分钟
                "preload": False,
            },
            # 技术指标 - 使用多级缓存，短TTL
            "stock_metrics": {
                "use_multi_level": True,
                "redis_ttl": 1800,  # 30分钟
                "memory_ttl": 300,  # 5分钟
                "preload": False,
            },
            # 筛选结果 - 仅使用Redis，短TTL
            "filter_result": {
                "use_multi_level": False,
                "redis_ttl": 900,  # 15分钟
                "memory_ttl": 300,  # 5分钟
                "preload": False,
            },
            # API缓存 - 使用多级缓存，短TTL
            "api_cache": {
                "use_multi_level": True,
                "redis_ttl": 900,  # 15分钟
                "memory_ttl": 180,  # 3分钟
                "preload": False,
            },
        }

    async def get_stock_info(
        self, stock_code: str, market: str = "A_share"
    ) -> Any | None:
        """获取股票基本信息

        Args:
            stock_code: 股票代码
            market: 市场类型

        Returns:
            股票信息
        """
        key = self.key_manager.generate_key("stock_info", stock_code, market=market)
        strategy = self.cache_strategies["stock_info"]

        if strategy["use_multi_level"]:
            return await self.multi_cache.get(key)
        else:
            return await self.redis_cache.get(key)

    async def set_stock_info(
        self, stock_code: str, data: Any, market: str = "A_share"
    ) -> bool:
        """设置股票基本信息

        Args:
            stock_code: 股票代码
            data: 股票数据
            market: 市场类型

        Returns:
            操作是否成功
        """
        key = self.key_manager.generate_key("stock_info", stock_code, market=market)
        strategy = self.cache_strategies["stock_info"]

        if strategy["use_multi_level"]:
            return await self.multi_cache.set(
                key, data, ttl=strategy["redis_ttl"], l1_ttl=strategy["memory_ttl"]
            )
        else:
            return await self.redis_cache.set(key, data, ttl=strategy["redis_ttl"])

    async def get_stock_daily_data(
        self, stock_code: str, date_str: str, market: str = "A_share"
    ) -> Any | None:
        """获取股票日线数据

        Args:
            stock_code: 股票代码
            date_str: 日期字符串
            market: 市场类型

        Returns:
            日线数据
        """
        key = self.key_manager.generate_key("stock_daily", stock_code, date_str, market)
        strategy = self.cache_strategies["stock_daily"]

        if strategy["use_multi_level"]:
            return await self.multi_cache.get(key)
        else:
            return await self.redis_cache.get(key)

    async def set_stock_daily_data(
        self, stock_code: str, date_str: str, data: Any, market: str = "A_share"
    ) -> bool:
        """设置股票日线数据

        Args:
            stock_code: 股票代码
            date_str: 日期字符串
            data: 日线数据
            market: 市场类型

        Returns:
            操作是否成功
        """
        key = self.key_manager.generate_key("stock_daily", stock_code, date_str, market)
        strategy = self.cache_strategies["stock_daily"]

        if strategy["use_multi_level"]:
            success = await self.multi_cache.set(
                key, data, ttl=strategy["redis_ttl"], l1_ttl=strategy["memory_ttl"]
            )
            return success
        else:
            success = await self.redis_cache.set(key, data, ttl=strategy["redis_ttl"])
            return success

    async def get_stock_metrics(
        self, stock_code: str, date_str: str, market: str = "A_share"
    ) -> Any | None:
        """获取股票技术指标

        Args:
            stock_code: 股票代码
            date_str: 日期字符串
            market: 市场类型

        Returns:
            技术指标数据
        """
        key = self.key_manager.generate_key(
            "stock_metrics", stock_code, date_str, market
        )
        strategy = self.cache_strategies["stock_metrics"]

        if strategy["use_multi_level"]:
            return await self.multi_cache.get(key)
        else:
            return await self.redis_cache.get(key)

    async def set_stock_metrics(
        self, stock_code: str, date_str: str, data: Any, market: str = "A_share"
    ) -> bool:
        """设置股票技术指标

        Args:
            stock_code: 股票代码
            date_str: 日期字符串
            data: 技术指标数据
            market: 市场类型

        Returns:
            操作是否成功
        """
        key = self.key_manager.generate_key(
            "stock_metrics", stock_code, date_str, market
        )
        strategy = self.cache_strategies["stock_metrics"]

        if strategy["use_multi_level"]:
            success = await self.multi_cache.set(
                key, data, ttl=strategy["redis_ttl"], l1_ttl=strategy["memory_ttl"]
            )
            return success
        else:
            success = await self.redis_cache.set(key, data, ttl=strategy["redis_ttl"])
            return success

    async def get_filter_result(self, filter_hash: str) -> Any | None:
        """获取筛选结果

        Args:
            filter_hash: 筛选条件哈希

        Returns:
            筛选结果
        """
        key = self.key_manager.generate_key("filter_result", filter_hash)
        return await self.redis_cache.get(key)

    async def set_filter_result(self, filter_hash: str, data: Any) -> bool:
        """设置筛选结果

        Args:
            filter_hash: 筛选条件哈希
            data: 筛选结果

        Returns:
            操作是否成功
        """
        key = self.key_manager.generate_key("filter_result", filter_hash)
        strategy = self.cache_strategies["filter_result"]
        return await self.redis_cache.set(key, data, ttl=strategy["redis_ttl"])

    def invalidate_stock_data(self, stock_code: str, market: str = "A_share"):
        """失效股票相关的所有缓存

        Args:
            stock_code: 股票代码
            market: 市场类型
        """
        patterns = [
            self.key_manager.generate_pattern("stock_info", f"{stock_code}*"),
            self.key_manager.generate_pattern("stock_daily", f"{stock_code}*"),
            self.key_manager.generate_pattern("stock_metrics", f"{stock_code}*"),
        ]

        for pattern in patterns:
            deleted_count = self.redis_cache.delete_pattern(pattern)
            logger.info(
                f"Invalidated {deleted_count} cache entries for pattern: {pattern}"
            )

        # 清理内存缓存中的相关项
        # 注意：这里简化处理，实际应该实现更精确的模式匹配删除
        logger.info(f"Invalidated cache for stock: {stock_code}")

    def invalidate_market_data(self, market: str, date_str: str | None = None):
        """失效市场相关的缓存

        Args:
            market: 市场类型
            date_str: 特定日期（可选）
        """
        if date_str:
            patterns = [
                self.key_manager.generate_pattern(
                    "stock_daily", f"*:{date_str}:{market}*"
                ),
                self.key_manager.generate_pattern(
                    "stock_metrics", f"*:{date_str}:{market}*"
                ),
            ]
        else:
            patterns = [
                self.key_manager.generate_pattern("stock_daily", f"*:{market}*"),
                self.key_manager.generate_pattern("stock_metrics", f"*:{market}*"),
            ]

        for pattern in patterns:
            deleted_count = self.redis_cache.delete_pattern(pattern)
            logger.info(
                f"Invalidated {deleted_count} cache entries for pattern: {pattern}"
            )

    def preload_hot_data(self, stock_codes: list[str], market: str = "A_share"):
        """预加载热点数据

        Args:
            stock_codes: 股票代码列表
            market: 市场类型
        """
        logger.info(f"Starting preload for {len(stock_codes)} stocks in {market}")

        # 这里应该实现具体的预加载逻辑
        # 例如：从数据库加载数据并设置到缓存中
        # 由于涉及具体的数据获取逻辑，这里只是框架

        for stock_code in stock_codes:
            try:
                # 预加载股票基本信息
                info_key = self.key_manager.generate_key(
                    "stock_info", stock_code, market=market
                )
                if not self.redis_cache.exists(info_key):
                    # 这里应该调用实际的数据获取函数
                    # stock_info = fetch_stock_info(stock_code, market)
                    # self.set_stock_info(stock_code, stock_info, market)
                    pass

            except Exception as e:
                logger.error(f"Failed to preload data for {stock_code}: {e}")

        logger.info("Preload completed")

    async def get(self, key: str) -> Any | None:
        """获取缓存数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据，如果不存在则返回none
        """
        try:
            # 先尝试从内存缓存获取
            value = await self.multi_cache.get(key)
            if value is not None:
                return value

            # 再从 Redis 获取
            value = await self.redis_cache.get(key)
            if value is not None:
                # 将 Redis 中的值同步到内存缓存
                await self.multi_cache.set(key, value, ttl=300)  # 5分钟TTL
            return value
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存数据

        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 过期时间（秒）

        Returns:
            操作是否成功
        """
        try:
            # 同时设置到内存缓存和Redis
            memory_success = await self.multi_cache.set(key, value, ttl=ttl or 300)
            redis_success = await self.redis_cache.set(key, value, ttl=ttl or 3600)
            return bool(memory_success and redis_success)
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存数据

        Args:
            key: 缓存键

        Returns:
            操作是否成功
        """
        try:
            # 从内存缓存和Redis中删除
            memory_success = self.multi_cache.delete(key)
            redis_success = self.redis_cache.delete(key)
            return memory_success or redis_success  # 只要有一个成功就算成功
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            键是否存在
        """
        try:
            # 先检查内存缓存
            if self.multi_cache.exists(key):
                return True
            # 再检查Redis
            return self.redis_cache.exists(key)
        except Exception as e:
            logger.error(f"Failed to check cache existence for key {key}: {e}")
            return False

    def clear_by_pattern(self, pattern: str) -> int:
        """按模式清理缓存

        Args:
            pattern: 缓存键模式

        Returns:
            删除的键数量
        """
        try:
            # 清除Redis中匹配的键
            redis_count = self.redis_cache.delete_pattern(pattern)

            # 清除内存缓存中匹配的键（简化实现）
            memory_count = 0
            # 注意：这里需要根据实际的multi_cache实现来调整

            logger.info(f"Cleared cache pattern: {pattern}, deleted: {redis_count}")
            return redis_count + memory_count
        except Exception as e:
            logger.error(f"Failed to clear cache by pattern {pattern}: {e}")
            return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息
        """
        try:
            redis_info = self.redis_cache.get_info()

            # 获取总键数
            keys = self.redis_cache.redis_client.keys("*")
            total_keys = len(keys)

            # 获取内存使用情况
            memory_usage = redis_info.get("used_memory_human", "0B")

            # 计算命中率和未命中率
            hit_count = getattr(self, "hit_count", 0)
            miss_count = getattr(self, "miss_count", 0)
            total_requests = hit_count + miss_count

            hit_rate = hit_count / total_requests if total_requests > 0 else 0.0
            miss_rate = miss_count / total_requests if total_requests > 0 else 0.0

            return {
                "total_keys": total_keys,
                "memory_usage": memory_usage,
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
                "redis": redis_info,
                "memory": self.memory_cache.get_stats(),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def health_check(self) -> bool:
        """缓存健康检查

        Returns:
            健康检查结果
        """
        try:
            # 测试Redis连接
            self.redis_cache.ping()

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
            logger.error(f"Cache health check failed: {e}")
            return False

    def get_comprehensive_stats(self) -> dict[str, Any]:
        """获取综合缓存统计信息

        Returns:
            包含所有缓存层统计信息的字典
        """
        return {
            "multi_level_cache": self.multi_cache.get_combined_stats(),
            "redis_cache": self.redis_cache.get_stats(),
            "memory_cache": self.memory_cache.get_stats(),
            "cache_strategies": self.cache_strategies,
        }

    def get_detailed_health_check(self) -> dict[str, Any]:
        """获取详细的缓存健康检查信息

        Returns:
            详细的健康检查结果
        """
        health_status = {
            "redis_connected": False,
            "memory_cache_active": False,
            "overall_status": "unhealthy",
        }

        try:
            # 检查Redis连接
            self.redis_cache.redis_client.ping()
            health_status["redis_connected"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")

        try:
            # 检查内存缓存
            test_key = "health_check_test"
            self.memory_cache.set(test_key, "test_value", ttl=10)
            if self.memory_cache.get(test_key) == "test_value":
                health_status["memory_cache_active"] = True
            self.memory_cache.delete(test_key)
        except Exception as e:
            logger.error(f"Memory cache health check failed: {e}")

        # 确定整体状态
        if health_status["redis_connected"] and health_status["memory_cache_active"]:
            health_status["overall_status"] = "healthy"
        elif health_status["redis_connected"] or health_status["memory_cache_active"]:
            health_status["overall_status"] = "degraded"

        return health_status

    def cleanup_expired(self):
        """清理过期缓存"""
        # 内存缓存会自动清理过期项
        # Redis缓存依赖TTL自动过期
        stats = self.memory_cache.cleanup_and_stats()
        logger.info(f"Cache cleanup completed. Memory cache stats: {stats}")

    def shutdown(self):
        """关闭缓存服务"""
        logger.info("Shutting down cache service...")

        try:
            self.memory_cache.shutdown()
            self.redis_cache.close()
            logger.info("Cache service shutdown completed")
        except Exception as e:
            logger.error(f"Error during cache service shutdown: {e}")


# 全局缓存服务实例
cache_service = CacheService()


def smart_cache(
    key_type: str, identifier_func: Callable | None = None, ttl: int | None = None
):
    """智能缓存装饰器

    根据数据类型自动选择合适的缓存策略

    Args:
        key_type: 缓存键类型
        identifier_func: 自定义标识符生成函数
        ttl: 自定义TTL（覆盖默认策略）

    Example:
        @smart_cache('stock_info', lambda code, market: f"{code}_{market}")
        def get_stock_info(stock_code: str, market: str):
            return fetch_stock_info_from_db(stock_code, market)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # 默认使用第一个参数作为标识符
                identifier = str(args[0]) if args else "default"

            key = cache_service.key_manager.generate_key(key_type, identifier)

            # 根据策略选择缓存方法
            strategy = cache_service.cache_strategies.get(
                key_type, {"use_multi_level": False, "redis_ttl": 3600}
            )

            # 尝试从缓存获取
            if strategy["use_multi_level"]:
                cached_result = cache_service.multi_cache.get(key)
            else:
                cached_result = await cache_service.redis_cache.get(key)

            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            if result is not None:
                # 注意：由于装饰器在同步上下文中，暂时跳过缓存设置
                # 在实际使用中，建议使用异步装饰器或在异步上下文中调用
                try:
                    logger.debug(f"Skipping cache set for {key} in sync context")
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")

            return result

        return wrapper

    return decorator
