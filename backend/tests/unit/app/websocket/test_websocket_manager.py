#!/usr/bin/env python3
"""
WebSocket连接管理器单元测试
不依赖服务器启动，直接测试WebSocket连接管理器的逻辑
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket

from app.websocket.connection_manager import ConnectionManager


class TestConnectionManager:
    """WebSocket连接管理器单元测试"""

    @pytest.fixture(autouse=True)
    def mock_heartbeat(self, mocker):
        """Mock the heartbeat monitor to do nothing."""

        async def dummy_monitor(*args, **kwargs):
            pass

        mocker.patch(
            "app.websocket.connection_manager.ConnectionManager._heartbeat_monitor",
            new=dummy_monitor,
        )

    @pytest.fixture
    def connection_manager(self):
        """创建WebSocket连接管理器实例"""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """创建模拟WebSocket连接"""
        websocket = AsyncMock(spec=WebSocket)
        websocket.client = MagicMock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 12345
        websocket.client_state = MagicMock()
        websocket.client_state.name = "CONNECTED"
        return websocket

    @pytest.mark.asyncio
    async def test_connect_client(self, connection_manager, mock_websocket):
        """测试客户端连接"""
        client_id = "test_client_001"

        # 连接客户端
        result = await connection_manager.connect(mock_websocket, client_id)

        # 验证连接已建立
        assert result is True
        assert client_id in connection_manager.active_connections
        assert connection_manager.active_connections[client_id] == mock_websocket
        assert len(connection_manager.active_connections) == 1
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_client(self, connection_manager, mock_websocket):
        """测试客户端断开连接"""
        client_id = "test_client_001"

        # 先连接
        await connection_manager.connect(mock_websocket, client_id)
        assert client_id in connection_manager.active_connections

        # 断开连接
        await connection_manager.disconnect(client_id)

        # 验证连接已断开
        assert client_id not in connection_manager.active_connections
        assert len(connection_manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_send_to_client(self, connection_manager, mock_websocket):
        """测试发送消息给客户端"""
        client_id = "test_client_001"
        message = {"type": "notification", "content": "Hello World"}

        # 连接客户端
        await connection_manager.connect(mock_websocket, client_id)

        # 重置mock以清除连接时的自动消息
        mock_websocket.send_text.reset_mock()

        # 发送消息
        result = await connection_manager.send_to_client(client_id, message)

        # 验证消息已发送
        assert result is True
        mock_websocket.send_text.assert_called_once_with(
            json.dumps(message, ensure_ascii=False)
        )

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_client(self, connection_manager):
        """测试向不存在的客户端发送消息"""
        client_id = "nonexistent_client"
        message = {"type": "notification", "content": "Hello World"}

        # 发送消息到不存在的客户端
        result = await connection_manager.send_to_client(client_id, message)

        # 验证发送失败
        assert result is False
        assert len(connection_manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_subscribe_to_topic(self, connection_manager, mock_websocket):
        """测试订阅主题"""
        client_id = "test_client_001"
        topic = "stock.AAPL.1m"

        # 连接客户端
        await connection_manager.connect(mock_websocket, client_id)

        # 订阅主题
        result = await connection_manager.subscribe(client_id, topic)

        # 验证订阅成功
        assert result is True
        assert topic in connection_manager.subscriptions
        assert client_id in connection_manager.subscriptions[topic]
        assert topic in connection_manager.client_subscriptions[client_id]

    @pytest.mark.asyncio
    async def test_unsubscribe_from_topic(self, connection_manager, mock_websocket):
        """测试取消订阅主题"""
        client_id = "test_client_001"
        topic = "stock.AAPL.1m"

        # 连接客户端并订阅
        await connection_manager.connect(mock_websocket, client_id)
        await connection_manager.subscribe(client_id, topic)

        # 取消订阅
        result = await connection_manager.unsubscribe(client_id, topic)

        # 验证取消订阅成功
        assert result is True
        if topic in connection_manager.subscriptions:
            assert client_id not in connection_manager.subscriptions[topic]
        if client_id in connection_manager.client_subscriptions:
            assert topic not in connection_manager.client_subscriptions[client_id]

    @pytest.mark.asyncio
    async def test_broadcast_to_topic(self, connection_manager):
        """测试向主题广播消息"""
        topic = "stock.AAPL.1m"
        message = {
            "type": "stock_update",
            "symbol": "AAPL",
            "price": 150.25,
            "timestamp": "2025-01-22T15:58:53",
        }

        # 创建订阅该主题的客户端
        subscribers = []
        for i in range(2):
            mock_ws = AsyncMock(spec=WebSocket)
            mock_ws.client = MagicMock()
            mock_ws.client.host = "127.0.0.1"
            mock_ws.client.port = 12345 + i
            mock_ws.client_state = MagicMock()
            mock_ws.client_state.name = "CONNECTED"
            client_id = f"subscriber_{i}"

            await connection_manager.connect(mock_ws, client_id)
            await connection_manager.subscribe(client_id, topic)
            subscribers.append((client_id, mock_ws))

        # 重置所有mock以清除连接时的自动消息
        for _, websocket in subscribers:
            websocket.send_text.reset_mock()

        # 广播消息到主题
        sent_count = await connection_manager.broadcast_to_topic(topic, message)

        # 验证所有订阅者都收到了消息
        assert sent_count == 2
        for _, websocket in subscribers:
            websocket.send_text.assert_called_once()
            sent_data = json.loads(websocket.send_text.call_args[0][0])
            assert sent_data["type"] == message["type"]
            assert sent_data["symbol"] == message["symbol"]
            assert sent_data["price"] == message["price"]
            assert sent_data["topic"] == topic
            assert "timestamp" in sent_data

    @pytest.mark.asyncio
    async def test_multiple_clients_same_topic(self, connection_manager):
        """测试多个客户端订阅同一主题"""
        topic = "stock.AAPL.1m"
        clients = []

        # 创建多个客户端订阅同一主题
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            mock_ws.client = MagicMock()
            mock_ws.client.host = "127.0.0.1"
            mock_ws.client.port = 12345 + i
            mock_ws.client_state = MagicMock()
            mock_ws.client_state.name = "CONNECTED"
            client_id = f"client_{i}"

            await connection_manager.connect(mock_ws, client_id)
            await connection_manager.subscribe(client_id, topic)
            clients.append((client_id, mock_ws))

        # 验证所有客户端都订阅了该主题
        assert topic in connection_manager.subscriptions
        assert len(connection_manager.subscriptions[topic]) == 3

        # 重置所有mock以清除连接时的自动消息
        for _, websocket in clients:
            websocket.send_text.reset_mock()

        # 广播消息
        message = {"type": "update", "data": "test"}
        sent_count = await connection_manager.broadcast_to_topic(topic, message)

        # 验证所有客户端都收到了消息
        assert sent_count == 3
        for _, websocket in clients:
            websocket.send_text.assert_called_once()
            sent_data = json.loads(websocket.send_text.call_args[0][0])
            assert sent_data["type"] == message["type"]
            assert sent_data["data"] == message["data"]
            assert sent_data["topic"] == topic
            assert "timestamp" in sent_data

    @pytest.mark.asyncio
    async def test_client_disconnect_removes_subscriptions(
        self, connection_manager, mock_websocket
    ):
        """测试客户端断开连接时自动取消所有订阅"""
        client_id = "test_client_001"
        topics = ["stock.AAPL.1m", "stock.GOOGL.1m", "crypto.BTC.1m"]

        # 连接客户端并订阅多个主题
        await connection_manager.connect(mock_websocket, client_id)
        for topic in topics:
            await connection_manager.subscribe(client_id, topic)

        # 验证订阅成功
        for topic in topics:
            assert topic in connection_manager.subscriptions
            assert client_id in connection_manager.subscriptions[topic]

        # 断开连接
        await connection_manager.disconnect(client_id)

        # 验证客户端从所有订阅中移除
        for topic in topics:
            if topic in connection_manager.subscriptions:
                assert client_id not in connection_manager.subscriptions[topic]

    def test_get_connection_stats(self, connection_manager):
        """测试获取连接统计信息"""
        stats = connection_manager.get_connection_stats()

        # 验证统计信息结构
        assert "total_connections" in stats
        assert "total_subscriptions" in stats
        assert "topics_count" in stats
        assert "connections" in stats
        assert stats["total_connections"] == 0
        assert stats["total_subscriptions"] == 0

    def test_get_topic_subscribers(self, connection_manager):
        """测试获取主题订阅者列表"""
        topic = "test_topic"

        # 测试不存在的主题
        subscribers = connection_manager.get_topic_subscribers(topic)
        assert len(subscribers) == 0

        # 添加订阅后测试
        connection_manager.subscriptions[topic] = {"client1", "client2"}
        subscribers = connection_manager.get_topic_subscribers(topic)
        assert len(subscribers) == 2
        assert "client1" in subscribers
        assert "client2" in subscribers
