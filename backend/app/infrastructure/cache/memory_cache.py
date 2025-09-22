from __future__ import annotations
from typing import Union

# !/usr/bin/env python3
"""

应用级内存缓存管理器
实现L1级别的高速内存缓存，与Redis缓存形成多级缓存架构
"""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheItem:
    """缓存项数据结构"""

    value: Any
    created_at: float
    expires_at: Union[float, None]
    access_count: int = 0
    last_accessed: float = 0

    def __post_init__(self):
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self):
        """更新访问时间和计数"""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUMemoryCache:
    """LRU内存缓存实现"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化LRU缓存

        Args:
            max_size: 最大缓存项数量
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheItem] = OrderedDict()
        self._lock = threading.RLock()

        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "expired_cleanups": 0,
        }

        # 清理线程控制
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """启动后台清理线程"""

        def cleanup_worker():
            while not self._stop_cleanup.wait(60):  # 每60秒清理一次
                self._cleanup_expired()

        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.debug("Memory cache cleanup thread started")

    def _cleanup_expired(self):
        """清理过期项"""
        with self._lock:
            expired_keys = []
            for key, item in self._cache.items():
                if item.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                self.stats["expired_cleanups"] += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")

    def _evict_lru(self):
        """淘汰最少使用的项"""
        if self._cache:
            evicted_key, _ = self._cache.popitem(last=False)
            self.stats["evictions"] += 1
            logger.debug(f"Evicted LRU item: {evicted_key}")

    def get(self, key: str) -> Union[Any, None]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期返回None
        """
        with self._lock:
            if key not in self._cache:
                self.stats["misses"] += 1
                return None

            item = self._cache[key]

            # 检查是否过期
            if item.is_expired():
                del self._cache[key]
                self.stats["misses"] += 1
                self.stats["expired_cleanups"] += 1
                return None

            # 更新访问信息并移到末尾（最近使用）
            item.touch()
            self._cache.move_to_end(key)
            self.stats["hits"] += 1

            return item.value

    def set(self, key: str, value: Any, ttl: Union[int, None] = None) -> bool:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示使用默认TTL

        Returns:
            操作是否成功
        """
        with self._lock:
            try:
                current_time = time.time()

                # 计算过期时间
                if ttl is None:
                    ttl = self.default_ttl

                expires_at = current_time + ttl if ttl > 0 else None

                # 创建缓存项
                item = CacheItem(
                    value=value, created_at=current_time, expires_at=expires_at
                )

                # 如果键已存在，更新并移到末尾
                if key in self._cache:
                    self._cache[key] = item
                    self._cache.move_to_end(key)
                else:
                    # 检查是否需要淘汰
                    while len(self._cache) >= self.max_size:
                        self._evict_lru()

                    self._cache[key] = item

                self.stats["sets"] += 1
                return True

            except Exception as e:
                logger.error(f"Failed to set cache item {key}: {e}")
                return False

    def delete(self, key: str) -> bool:
        """删除缓存项

        Args:
            key: 缓存键

        Returns:
            操作是否成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats["deletes"] += 1
                return True
            return False

    def exists(self, key: str) -> bool:
        """检查缓存是否存在且未过期

        Args:
            key: 缓存键

        Returns:
            缓存是否存在且有效
        """
        with self._lock:
            if key not in self._cache:
                return False

            item = self._cache[key]
            if item.is_expired():
                del self._cache[key]
                self.stats["expired_cleanups"] += 1
                return False

            return True

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {cleared_count} cache items")

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            包含统计信息的字典
        """
        with self._lock:
            total_operations = self.stats["hits"] + self.stats["misses"]
            hit_rate = (
                (self.stats["hits"] / total_operations * 100)
                if total_operations > 0
                else 0
            )

            # 计算内存使用情况（估算）
            cache_size = len(self._cache)
            memory_usage_mb = cache_size * 0.001  # 粗略估算，每项1KB

            return {
                "cache_stats": self.stats.copy(),
                "hit_rate": round(hit_rate, 2),
                "cache_size": cache_size,
                "max_size": self.max_size,
                "memory_usage_mb": round(memory_usage_mb, 2),
                "utilization": round((cache_size / self.max_size * 100), 2),
                "last_updated": datetime.now().isoformat(),
            }

    def get_item_info(self, key: str) -> Union[dict[str, Any], None]:
        """获取缓存项详细信息

        Args:
            key: 缓存键

        Returns:
            缓存项信息字典
        """
        with self._lock:
            if key not in self._cache:
                return None

            item = self._cache[key]
            current_time = time.time()

            return {
                "key": key,
                "created_at": datetime.fromtimestamp(item.created_at).isoformat(),
                "expires_at": (
                    datetime.fromtimestamp(item.expires_at).isoformat()
                    if item.expires_at
                    else None
                ),
                "last_accessed": datetime.fromtimestamp(item.last_accessed).isoformat(),
                "access_count": item.access_count,
                "ttl_remaining": (
                    int(item.expires_at - current_time) if item.expires_at else None
                ),
                "is_expired": item.is_expired(),
                "age_seconds": int(current_time - item.created_at),
            }

    def get_hot_keys(self, limit: int = 10) -> list[tuple[str, int]]:
        """获取热点键（按访问次数排序）

        Args:
            limit: 返回的键数量限制

        Returns:
            (键, 访问次数)的列表
        """
        with self._lock:
            items = [(key, item.access_count) for key, item in self._cache.items()]
            items.sort(key=lambda x: x[1], reverse=True)
            return items[:limit]

    def cleanup_and_stats(self) -> dict[str, Any]:
        """执行清理并返回统计信息

        Returns:
            清理后的统计信息
        """
        self._cleanup_expired()
        return self.get_stats()

    def shutdown(self):
        """关闭缓存，停止后台线程"""
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Memory cache shutdown completed")


class MultiLevelCache:
    """多级缓存管理器

    结合内存缓存(L1)和Redis缓存(L2)，提供透明的多级缓存访问
    """

    def __init__(self, memory_cache: LRUMemoryCache, redis_cache):
        """
        初始化多级缓存

        Args:
            memory_cache: L1内存缓存实例
            redis_cache: L2 Redis缓存实例
        """
        self.l1_cache = memory_cache
        self.l2_cache = redis_cache

        # 多级缓存统计
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "total_misses": 0,
            "l1_to_l2_promotions": 0,
        }

    async def get(self, key: str) -> Union[Any, None]:
        """多级缓存获取

        先从L1获取，如果未命中则从L2获取并提升到L1

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        # 尝试从L1获取
        value = self.l1_cache.get(key)
        if value is not None:
            self.stats["l1_hits"] += 1
            return value

        # 尝试从L2获取
        value = await self.l2_cache.get(key)
        if value is not None:
            self.stats["l2_hits"] += 1
            self.stats["l1_to_l2_promotions"] += 1

            # 提升到L1缓存
            self.l1_cache.set(key, value, ttl=300)  # L1使用较短的TTL
            return value

        # 完全未命中
        self.stats["total_misses"] += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Union[int, None] = None,
        l1_ttl: Union[int, None] = None,
    ) -> bool:
        """多级缓存设置

        同时设置L1和L2缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: L2缓存TTL
            l1_ttl: L1缓存TTL（默认为ttl的1/4或300秒）

        Returns:
            操作是否成功
        """
        # 设置L2缓存
        l2_success = await self.l2_cache.set(key, value, ttl=ttl)

        # 设置L1缓存（使用较短的TTL）
        if l1_ttl is None:
            l1_ttl = min(ttl // 4 if ttl else 300, 300)

        l1_success = self.l1_cache.set(key, value, ttl=l1_ttl)

        return l2_success and l1_success

    def delete(self, key: str) -> bool:
        """多级缓存删除

        同时删除L1和L2缓存

        Args:
            key: 缓存键

        Returns:
            操作是否成功
        """
        l1_success = self.l1_cache.delete(key)
        l2_success = self.l2_cache.delete(key)

        return l1_success or l2_success

    def exists(self, key: str) -> bool:
        """检查多级缓存中是否存在指定键

        先检查L1缓存，如果不存在再检查L2缓存

        Args:
            key: 缓存键

        Returns:
            键是否存在
        """
        # 先检查L1缓存
        if self.l1_cache.exists(key):
            return True

        # 再检查L2缓存
        return self.l2_cache.exists(key)

    def get_combined_stats(self) -> dict[str, Any]:
        """获取多级缓存统计信息

        Returns:
            包含L1、L2和整体统计的字典
        """
        l1_stats = self.l1_cache.get_stats()
        l2_stats = self.l2_cache.get_stats()

        total_hits = self.stats["l1_hits"] + self.stats["l2_hits"]
        total_operations = total_hits + self.stats["total_misses"]
        overall_hit_rate = (
            (total_hits / total_operations * 100) if total_operations > 0 else 0
        )

        return {
            "multi_level_stats": self.stats.copy(),
            "overall_hit_rate": round(overall_hit_rate, 2),
            "l1_cache": l1_stats,
            "l2_cache": l2_stats,
            "last_updated": datetime.now().isoformat(),
        }


# 全局内存缓存实例
memory_cache = LRUMemoryCache(max_size=1000, default_ttl=300)


def memory_cache_result(ttl: int = 300):
    """内存缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）

    Example:
        @memory_cache_result(ttl=600)
        def expensive_calculation(param1, param2):
            return complex_computation(param1, param2)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            import hashlib
            import json

            func_name = func.__name__
            args_str = json.dumps([args, kwargs], default=str, sort_keys=True)
            key_hash = hashlib.sha256(args_str.encode()).hexdigest()[:8]
            cache_key = f"mem:{func_name}:{key_hash}"

            # 尝试从缓存获取
            cached_result = memory_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            if result is not None:
                memory_cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator
