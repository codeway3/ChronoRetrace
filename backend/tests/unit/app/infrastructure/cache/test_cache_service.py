#!/usr/bin/env python3
"""
ChronoRetrace - 缓存服务单元测试

本模块包含缓存服务相关功能的单元测试，包括Redis缓存、缓存键管理、
缓存预热等功能的测试用例。

Author: ChronoRetrace Team
Date: 2024
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.cache.cache_warming import (
    CacheWarmingService,
)
from app.infrastructure.cache.redis_manager import CacheKeyManager


class TestCacheService:
    """缓存服务测试类"""

    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = 0
        mock_redis.keys.return_value = []
        mock_redis.info.return_value = {"used_memory_human": "1MB"}
        mock_redis.ping.return_value = True
        return mock_redis

    @pytest.fixture
    def cache_service(self, mock_redis):
        """创建缓存服务实例"""
        service = CacheService()
        # 模拟redis_cache属性
        service.redis_cache = Mock()
        service.redis_cache.get = AsyncMock(return_value=None)
        service.redis_cache.set.return_value = True
        service.redis_cache.delete.return_value = True
        service.redis_cache.exists.return_value = False
        service.redis_cache.delete_pattern.return_value = 2
        service.redis_cache.ping.return_value = True
        service.redis_cache.get_info.return_value = {"used_memory_human": "2MB"}
        service.redis_cache.redis_client = mock_redis

        # 模拟memory_cache
        service.memory_cache = Mock()
        service.memory_cache.get.return_value = None
        service.memory_cache.set.return_value = True
        service.memory_cache.delete.return_value = True
        service.memory_cache.exists.return_value = False
        service.memory_cache.get_stats.return_value = {"hits": 0, "misses": 0}

        # 模拟multi_cache
        service.multi_cache = Mock()
        service.multi_cache.get = AsyncMock(return_value=None)
        service.multi_cache.set.return_value = True
        service.multi_cache.delete.return_value = True
        service.multi_cache.exists.return_value = False

        return service

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_service, mock_redis):
        """测试缓存未命中"""
        cache_service.multi_cache.get.return_value = None
        cache_service.redis_cache.get.return_value = None

        result = await cache_service.get("test_key")

        assert result is None
        cache_service.redis_cache.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_service, mock_redis):
        """测试缓存命中"""
        test_data = {"stock_code": "000001", "price": 10.5}
        cache_service.multi_cache.get.return_value = test_data

        result = await cache_service.get("test_key")

        assert result == test_data
        # 由于从multi_cache命中，不应该调用redis_cache.get
        cache_service.redis_cache.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_cache(self, cache_service, mock_redis):
        """测试设置缓存"""
        test_data = {"stock_code": "000001", "price": 10.5}
        cache_service.multi_cache.set = AsyncMock(return_value=True)
        cache_service.redis_cache.set = AsyncMock(return_value=True)

        result = await cache_service.set("test_key", test_data, ttl=3600)

        assert result is True
        cache_service.redis_cache.set.assert_called_once_with(
            "test_key", test_data, ttl=3600
        )
        cache_service.multi_cache.set.assert_called_once_with(
            "test_key", test_data, ttl=3600
        )

    @pytest.mark.asyncio
    async def test_delete_cache(self, cache_service, mock_redis):
        """测试删除缓存"""
        cache_service.multi_cache.delete.return_value = True
        cache_service.redis_cache.delete.return_value = True

        result = cache_service.delete("test_key")

        assert result is True
        cache_service.redis_cache.delete.assert_called_once_with("test_key")
        cache_service.multi_cache.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_cache(self, cache_service, mock_redis):
        """测试检查缓存是否存在"""
        cache_service.multi_cache.exists.return_value = True

        result = cache_service.exists("test_key")

        assert result is True
        cache_service.multi_cache.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_clear_by_pattern(self, cache_service, mock_redis):
        """测试按模式清理缓存"""
        cache_service.redis_cache.delete_pattern.return_value = 2

        result = cache_service.clear_by_pattern("stock:*")

        assert result == 2
        cache_service.redis_cache.delete_pattern.assert_called_once_with("stock:*")

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_service, mock_redis):
        """测试获取缓存统计"""
        cache_service.redis_cache.get_info.return_value = {"used_memory_human": "2MB"}
        mock_redis.keys.return_value = ["key1", "key2", "key3"]

        # 模拟缓存命中率统计
        cache_service.hit_count = 80
        cache_service.miss_count = 20

        stats = cache_service.get_cache_stats()

        assert stats["total_keys"] == 3
        assert stats["memory_usage"] == "2MB"
        assert stats["hit_rate"] == 0.8
        assert stats["miss_rate"] == 0.2

    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_service, mock_redis):
        """测试健康检查成功"""
        # 设置ping成功
        cache_service.redis_cache.ping.return_value = True

        # 设置set/get/delete操作成功
        cache_service.multi_cache.get.return_value = "test"
        cache_service.multi_cache.set.return_value = True
        cache_service.multi_cache.delete.return_value = True
        cache_service.redis_cache.set.return_value = True
        cache_service.redis_cache.delete.return_value = True

        result = await cache_service.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, cache_service, mock_redis):
        """测试健康检查失败"""
        mock_redis.ping.side_effect = Exception("Connection failed")

        result = await cache_service.health_check()

        assert result is False


class TestCacheKeyManager:
    """缓存键管理器测试类"""

    def test_stock_info_key(self):
        """测试股票信息键生成"""
        key = CacheKeyManager.generate_key("stock_info", "000001.SZ")
        assert "stock:info" in key
        assert "000001.SZ" in key
        assert isinstance(key, str)

    def test_stock_data_key(self):
        """测试股票数据键生成"""
        key = CacheKeyManager.generate_key("stock_daily", "000001.SZ", "2024-01-01")
        assert "stock:daily" in key
        assert "000001.SZ" in key
        assert isinstance(key, str)

    def test_filter_result_key(self):
        """测试过滤结果键生成"""
        key = CacheKeyManager.generate_key("filter_result", "test_filter")
        assert "filter:result" in key
        assert "test_filter" in key
        assert isinstance(key, str)

    def test_user_session_key(self):
        """测试用户会话键生成"""
        key = CacheKeyManager.generate_key("user_session", "user123")
        assert "user:session" in key
        assert "user123" in key
        assert isinstance(key, str)

    def test_api_cache_key(self):
        """测试API缓存键生成"""
        key = CacheKeyManager.generate_key("api_cache", "endpoint_hash")
        assert "api:cache" in key
        assert "endpoint_hash" in key
        assert isinstance(key, str)

    def test_key_with_hash(self):
        """测试带哈希的键生成"""
        params = {"param1": "value1", "param2": "value2"}
        key = CacheKeyManager.generate_key_with_hash("api_cache", "test", params)
        assert "api:cache" in key
        assert "test" in key
        assert isinstance(key, str)


class TestCacheWarmingService:
    """缓存预热服务测试类"""

    @pytest.fixture
    def mock_cache_service(self):
        """模拟缓存服务"""
        mock_service = Mock()
        mock_service.set = Mock(return_value=True)
        mock_service.get = Mock(return_value=None)
        mock_service.delete = Mock(return_value=True)
        mock_service.exists = Mock(return_value=False)
        mock_service.clear_by_pattern = Mock(return_value=5)
        mock_service.health_check = Mock(return_value=True)
        return mock_service

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        mock_session = Mock()
        mock_session.query.return_value.all.return_value = [
            Mock(ts_code="000001.SZ", name="平安银行"),
            Mock(ts_code="000002.SZ", name="万科A"),
        ]
        return mock_session

    @pytest.fixture
    def warming_service(self, mock_cache_service):
        """创建缓存预热服务实例"""
        service = CacheWarmingService()
        service.cache_service = mock_cache_service
        return service

    @pytest.mark.asyncio
    async def test_warm_cache(self, warming_service, mock_cache_service):
        """测试缓存预热"""

        with patch(
            "app.infrastructure.cache.cache_warming.SessionLocal"
        ) as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = [
                Mock(ts_code="000001", name="平安银行", industry="银行"),
                Mock(ts_code="000002", name="万科A", industry="房地产"),
            ]

            result = await warming_service.warm_cache()

            assert result["status"] == "completed"
            assert result["warmed_count"] >= 2
            assert mock_cache_service.set.call_count >= 2

    @pytest.mark.asyncio
    async def test_get_hot_stocks(self, warming_service, mock_cache_service):
        """测试获取热门股票"""
        with patch(
            "app.infrastructure.cache.cache_warming.SessionLocal"
        ) as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value.__enter__.return_value = mock_session
            mock_session.execute.return_value.fetchall.return_value = [
                ("000001.SZ",),
                ("000002.SZ",),
                ("000003.SZ",),
            ]

            result = await warming_service._get_hot_stocks()

            assert isinstance(result, list)
            assert len(result) >= 3

    @pytest.mark.asyncio
    async def test_incremental_update_stocks(self, warming_service, mock_cache_service):
        """测试增量更新股票"""
        stock_codes = ["000001.SZ", "000002.SZ"]

        with patch(
            "app.infrastructure.cache.cache_warming.SessionLocal"
        ) as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value.__enter__.return_value = mock_session

            # 创建正确的mock对象
            mock_stock1 = Mock()
            mock_stock1.ts_code = "000001.SZ"
            mock_stock1.trade_date = datetime.strptime("20240115", "%Y%m%d").date()
            mock_stock1.close = 10.5
            mock_stock1.open = 10.0
            mock_stock1.high = 11.0
            mock_stock1.low = 9.5
            mock_stock1.vol = 1000000

            mock_stock2 = Mock()
            mock_stock2.ts_code = "000002.SZ"
            mock_stock2.trade_date = datetime.strptime("20240115", "%Y%m%d").date()
            mock_stock2.close = 25.8
            mock_stock2.open = 25.0
            mock_stock2.high = 26.0
            mock_stock2.low = 24.5
            mock_stock2.vol = 2000000

            # 简化mock设置
            mock_query = Mock()
            mock_filter = Mock()
            mock_order = Mock()

            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_filter
            mock_filter.order_by.return_value = mock_order
            mock_order.first.return_value = mock_stock1

            result = await warming_service.incremental_update_stocks(stock_codes)

            assert result["status"] == "completed"
            assert result["updated_count"] == 2

    def test_get_warming_stats(self, warming_service):
        """测试获取预热统计"""
        # 设置一些统计数据
        warming_service.stats = {
            "total_warmed": 100,
            "last_warming_time": datetime.now(),
            "warming_duration": 30.5,
        }

        stats = warming_service.get_warming_stats()

        assert stats["total_warmed"] == 100
        assert "last_warming_time" in stats
        assert stats["warming_duration"] == 30.5

    def test_is_healthy(self, warming_service):
        """测试健康检查"""
        # 设置健康状态
        warming_service.stats = {"total_warmed": 100}

        result = warming_service.is_healthy()

        assert result is True

    @pytest.mark.asyncio
    async def test_warm_specific_stocks(self, warming_service, mock_cache_service):
        """测试预热指定股票"""
        stock_codes = ["000001", "000002"]

        with (
            patch.object(warming_service, "warm_stock_info") as mock_warm_info,
            patch.object(warming_service, "warm_stock_data") as mock_warm_data,
        ):
            mock_warm_info.return_value = {"status": "completed"}
            mock_warm_data.return_value = {"status": "completed"}

            result = await warming_service.warm_specific_stocks(stock_codes)

            assert result["status"] == "completed"
            assert result["warmed_stocks"] == 2
            assert mock_warm_info.call_count == 2
            assert mock_warm_data.call_count == 2


class TestCacheIntegration:
    """缓存集成测试类"""

    @pytest.mark.asyncio
    async def test_cache_workflow(self):
        """测试完整的缓存工作流程"""
        # 这里可以添加集成测试，测试缓存服务、预热服务等的协同工作
        pass

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """测试缓存性能"""
        # 这里可以添加性能测试，测试缓存的响应时间、吞吐量等
        pass


if __name__ == "__main__":
    pytest.main([__file__])
