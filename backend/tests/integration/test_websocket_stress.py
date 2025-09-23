#!/usr/bin/env python3
"""
WebSocket 压力测试
用于测试多个并发连接和消息处理
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.slow
def test_websocket_multiple_connections(client):
    """测试多个并发连接"""
    logger.info("测试: 多个并发连接")
    connection_count = 5  # 适中的连接数量

    def connect_and_send(i):
        try:
            with client.websocket_connect(f"/api/v1/ws/stress_client_{i}") as websocket:
                # 等待连接确认
                ack = websocket.receive_text()
                logger.info(f"客户端 stress_client_{i} 连接成功: {ack}")

                # 测试消息发送
                message = {"type": "subscribe", "topic": "stock.AAPL.1m"}
                websocket.send_text(json.dumps(message))
                logger.info(f"向连接 {i} 发送消息成功")
                return True
        except Exception as e:
            logger.error(f"客户端 stress_client_{i} 连接失败: {e}")
            return False

    with ThreadPoolExecutor(max_workers=connection_count) as executor:
        results = list(executor.map(connect_and_send, range(connection_count)))

    successful_connections = sum(results)
    logger.info(f"成功建立 {successful_connections}/{connection_count} 个连接")
    assert successful_connections > 0, "至少应该有一个连接成功"


@pytest.mark.integration
@pytest.mark.slow
def test_websocket_message_burst(client):
    """测试消息突发发送"""
    logger.info("测试: 消息突发发送")
    client_id = "burst_test_client"

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            # 等待连接确认
            ack = websocket.receive_text()
            logger.info(f"连接确认: {ack}")

            # 快速发送多条消息
            message_count = 10
            for i in range(message_count):
                message = {"type": "subscribe", "topic": f"stock.SYMBOL_{i}.1m"}
                websocket.send_text(json.dumps(message))

            logger.info(f"发送了 {message_count} 条消息")

            # 尝试接收响应
            responses = 0
            try:
                while responses < 5:  # 最多接收5个响应
                    response = websocket.receive_text()
                    responses += 1
                    logger.info(f"收到响应 {responses}: {response[:100]}...")
            except Exception:
                logger.info(f"总共收到 {responses} 个响应")

    except Exception as e:
        logger.error(f"消息突发测试失败: {e}")
        pytest.fail(f"消息突发测试失败: {e}")


@pytest.mark.integration
@pytest.mark.slow
def test_websocket_connection_lifecycle(client):
    """测试连接生命周期"""
    logger.info("测试: 连接生命周期")

    for cycle in range(3):  # 3个周期
        client_id = f"lifecycle_test_{cycle}"

        try:
            # 建立连接
            with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
                logger.info(f"周期 {cycle}: 连接建立")

                # 等待连接确认
                ack = websocket.receive_text()
                logger.info(f"周期 {cycle}: 连接确认 {ack}")

                # 发送订阅消息
                subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}
                websocket.send_text(json.dumps(subscribe_message))

                # 发送取消订阅消息
                unsubscribe_message = {"type": "unsubscribe", "topic": "stock.AAPL.1m"}
                websocket.send_text(json.dumps(unsubscribe_message))

                logger.info(f"周期 {cycle}: 连接关闭")

        except Exception as e:
            logger.warning(f"周期 {cycle} 失败: {e}")


@pytest.mark.integration
@pytest.mark.slow
def test_websocket_concurrent_operations(client):
    """测试并发操作"""
    logger.info("测试: 并发操作")

    def client_task(client_id: str):
        """单个客户端任务"""
        try:
            with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
                # 等待连接确认
                websocket.receive_text()
                logger.info(f"{client_id}: 连接确认")

                # 执行多个操作
                operations = [
                    {"type": "subscribe", "topic": "stock.AAPL.1m"},
                    {"type": "subscribe", "topic": "stock.GOOGL.1m"},
                    {"type": "ping"},
                    {"type": "unsubscribe", "topic": "stock.AAPL.1m"},
                ]

                for op in operations:
                    websocket.send_text(json.dumps(op))

                return True
        except Exception as e:
            logger.warning(f"{client_id} 任务失败: {e}")
            return False

    # 并发执行多个客户端任务
    client_count = 3
    with ThreadPoolExecutor(max_workers=client_count) as executor:
        results = list(
            executor.map(
                client_task, [f"concurrent_client_{i}" for i in range(client_count)]
            )
        )

    # 统计结果
    successful = sum(results)
    logger.info(f"并发操作结果: {successful}/{client_count} 成功")

    # 至少应该有一半的操作成功
    assert successful >= client_count // 2, f"成功率过低: {successful}/{client_count}"


@pytest.mark.integration
@pytest.mark.slow
def test_websocket_long_running_connection(client):
    """测试长时间运行的连接"""
    logger.info("测试: 长时间运行的连接")
    client_id = "long_running_client"

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            # 等待连接确认
            ack = websocket.receive_text()
            logger.info(f"连接确认: {ack}")

            # 订阅数据
            subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}
            websocket.send_text(json.dumps(subscribe_message))

            # 保持连接一段时间，定期发送心跳
            duration = 5  # 5秒
            start_time = time.time()

            while time.time() - start_time < duration:
                # 发送心跳
                ping_message = {"type": "ping"}
                websocket.send_text(json.dumps(ping_message))

                # 尝试接收消息
                try:
                    response = websocket.receive_text()
                    logger.info(f"收到消息: {response[:100]}...")
                except Exception:
                    logger.info("心跳周期内无消息")

                time.sleep(1)  # 1秒心跳间隔

            logger.info(f"长连接测试完成，持续时间: {duration}秒")

    except Exception as e:
        logger.error(f"长连接测试失败: {e}")
        pytest.fail(f"长连接测试失败: {e}")
