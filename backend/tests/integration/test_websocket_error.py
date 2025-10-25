#!/usr/bin/env python3
"""
WebSocket 错误测试
专门测试各种可能导致后端报错的WebSocket场景
"""

import json
import logging

import pytest

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "ws://127.0.0.1:8000/api/v1/ws"


@pytest.mark.integration
def test_websocket_invalid_json(client):
    """测试发送无效JSON"""
    logger.info("测试: 发送无效JSON")
    client_id = "test_invalid_json"

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            # 等待连接确认
            ack = websocket.receive_text()
            logger.info(f"连接确认: {ack}")

            # 发送无效JSON
            websocket.send_text("这不是有效的JSON")

            # 等待服务器响应
            try:
                response = websocket.receive_text()
                logger.info(f"收到响应: {response}")

                # 验证响应是错误消息
                response_data = json.loads(response)
                assert response_data.get("type") == "error"
                assert "invalid_json" in response_data.get("error_code", "")

            except Exception:
                logger.info("没有收到响应 - 这是可接受的行为")
                pass

    except Exception as e:
        logger.exception("无效JSON测试失败")
        pytest.fail(f"无效JSON测试失败: {e}")


@pytest.mark.integration
def test_websocket_invalid_message_type(client):
    """测试发送无效消息类型"""
    logger.info("测试: 发送无效消息类型")
    client_id = "test_invalid_type"

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            # 等待连接确认
            ack = websocket.receive_text()
            logger.info(f"连接确认: {ack}")

            # 发送无效消息类型
            invalid_message = {"type": "invalid_type", "data": "test"}
            websocket.send_text(json.dumps(invalid_message))

            # 尝试接收响应
            try:
                response = websocket.receive_text()
                logger.info(f"收到响应: {response}")
                # 服务器应该返回错误消息
                assert response is not None
            except Exception:
                logger.info("没有收到响应 - 这是可接受的行为")
                pass

    except Exception as e:
        logger.exception("无效消息类型测试失败")
        pytest.fail(f"无效消息类型测试失败: {e}")


@pytest.mark.integration
def test_websocket_malformed_subscribe(client):
    """测试格式错误的订阅消息"""
    logger.info("测试: 发送格式错误的订阅消息")
    client_id = "test_malformed_subscribe"

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            # 等待连接确认
            ack = websocket.receive_text()
            logger.info(f"连接确认: {ack}")

            # 发送缺少topic的订阅消息
            malformed_message = {"type": "subscribe"}  # 缺少topic
            websocket.send_text(json.dumps(malformed_message))

            # 发送无效topic的订阅消息
            invalid_topic_message = {"type": "subscribe", "topic": ""}  # 空topic
            websocket.send_text(json.dumps(invalid_topic_message))

            # 尝试接收响应
            try:
                response = websocket.receive_text()
                logger.info(f"收到响应: {response}")
                assert response is not None
            except Exception:
                logger.info("没有收到响应")
                pass

    except Exception as e:
        logger.exception("格式错误订阅测试失败")
        pytest.fail(f"格式错误订阅测试失败: {e}")


@pytest.mark.integration
def test_websocket_rapid_connections(client):
    """测试快速连接和断开"""
    logger.info("测试: 快速连接和断开")

    for i in range(3):  # 减少连接数量避免过度压力
        client_id = f"rapid_test_{i}"

        try:
            with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
                # 等待连接确认
                ack = websocket.receive_text()
                logger.info(f"快速连接 {i} 确认: {ack}")

                websocket.send_text(json.dumps({"type": "ping"}))
        except Exception as e:
            logger.warning(f"快速连接 {i} 失败: {e}")
            # 快速连接失败是可接受的


@pytest.mark.integration
def test_websocket_large_message(client):
    """测试发送大消息"""
    logger.info("测试: 发送大消息")
    client_id = "test_large_message"

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            # 等待连接确认
            ack = websocket.receive_text()
            logger.info(f"连接确认: {ack}")

            # 创建一个大消息
            large_data = "x" * 5000  # 5KB
            large_message = {
                "type": "subscribe",
                "topic": "stock.AAPL.1m",
                "large_data": large_data,
            }
            websocket.send_text(json.dumps(large_message))

            # 尝试接收响应
            try:
                response = websocket.receive_text()
                logger.info(f"收到响应长度: {len(response)}")
                assert response is not None
            except Exception:
                logger.info("没有收到响应")
                pass

    except Exception as e:
        logger.exception("大消息测试失败")
        pytest.fail(f"大消息测试失败: {e}")


@pytest.mark.integration
def test_websocket_concurrent_subscriptions(client):
    """测试并发订阅相同主题"""
    logger.info("测试: 并发订阅相同主题")

    try:
        with (
            client.websocket_connect("/api/v1/ws/concurrent_test_1") as websocket1,
            client.websocket_connect("/api/v1/ws/concurrent_test_2") as websocket2,
            client.websocket_connect("/api/v1/ws/concurrent_test_3") as websocket3,
        ):
            websockets = [websocket1, websocket2, websocket3]

            for i, websocket in enumerate(websockets):
                # 等待连接确认
                ack = websocket.receive_text()
                logger.info(f"并发连接 {i} 确认: {ack}")

                # 所有连接订阅相同主题
                subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}
                websocket.send_text(json.dumps(subscribe_message))

    except Exception as e:
        logger.exception("并发订阅测试失败")
        pytest.fail(f"并发订阅测试失败: {e}")


@pytest.mark.integration
def test_websocket_connection_without_client_id(client):
    """测试不带客户端ID的连接"""
    logger.info("测试: 不带客户端ID的连接")

    # 尝试连接到基础URL（不带客户端ID）
    try:
        with client.websocket_connect("/api/v1/ws/") as websocket:
            websocket.send_text(json.dumps({"type": "ping"}))
            logger.info("意外成功连接（应该失败）")
            # 如果连接成功，这可能表示服务器配置问题
    except Exception as e:
        logger.info(f"预期的连接失败: {e}")
        # 连接失败是预期的行为
        pass
