#!/usr/bin/env python3
"""
WebSocket 压力测试
用于测试多个并发连接和消息处理
"""

import asyncio
import json
import logging
import time

import pytest
import websockets

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "ws://127.0.0.1:8000/api/v1/ws"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_websocket_multiple_connections():
    """测试多个并发连接"""
    logger.info("测试: 多个并发连接")
    connections = []
    connection_count = 5  # 适中的连接数量

    try:
        # 创建多个连接
        for i in range(connection_count):
            client_id = f"stress_client_{i}"
            uri = f"{BASE_URL}/{client_id}"

            try:
                websocket = await websockets.connect(uri)
                connections.append(websocket)

                # 等待连接确认
                ack = await websocket.recv()
                logger.info(f"客户端 {client_id} 连接成功: {ack}")

            except Exception as e:
                logger.error(f"客户端 {client_id} 连接失败: {e}")

        # 验证连接数量
        successful_connections = len(connections)
        logger.info(f"成功建立 {successful_connections}/{connection_count} 个连接")
        assert successful_connections > 0, "至少应该有一个连接成功"

        # 测试消息发送
        for i, websocket in enumerate(connections):
            try:
                message = {
                    "type": "subscribe",
                    "topic": "stock.AAPL.1m"
                }
                await websocket.send(json.dumps(message))
                logger.info(f"向连接 {i} 发送消息成功")
            except Exception as e:
                logger.warning(f"向连接 {i} 发送消息失败: {e}")

        await asyncio.sleep(2)  # 等待处理

    except Exception as e:
        logger.error(f"多连接测试失败: {e}")
        pytest.fail(f"多连接测试失败: {e}")
    finally:
        # 清理连接
        for i, websocket in enumerate(connections):
            try:
                await websocket.close()
                logger.info(f"关闭连接 {i}")
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_websocket_message_burst():
    """测试消息突发发送"""
    logger.info("测试: 消息突发发送")
    client_id = "burst_test_client"
    uri = f"{BASE_URL}/{client_id}"

    try:
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            ack = await websocket.recv()
            logger.info(f"连接确认: {ack}")

            # 快速发送多条消息
            message_count = 10
            for i in range(message_count):
                message = {
                    "type": "subscribe",
                    "topic": f"stock.SYMBOL_{i}.1m"
                }
                await websocket.send(json.dumps(message))
                # 短暂延迟避免过度压力
                await asyncio.sleep(0.1)

            logger.info(f"发送了 {message_count} 条消息")

            # 等待处理
            await asyncio.sleep(3)

            # 尝试接收响应
            responses = 0
            try:
                while responses < 5:  # 最多接收5个响应
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    responses += 1
                    logger.info(f"收到响应 {responses}: {response[:100]}...")
            except asyncio.TimeoutError:
                logger.info(f"总共收到 {responses} 个响应")

    except Exception as e:
        logger.error(f"消息突发测试失败: {e}")
        pytest.fail(f"消息突发测试失败: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_websocket_connection_lifecycle():
    """测试连接生命周期"""
    logger.info("测试: 连接生命周期")

    for cycle in range(3):  # 3个周期
        client_id = f"lifecycle_test_{cycle}"
        uri = f"{BASE_URL}/{client_id}"

        try:
            # 建立连接
            websocket = await websockets.connect(uri)
            logger.info(f"周期 {cycle}: 连接建立")

            # 等待连接确认
            ack = await websocket.recv()
            logger.info(f"周期 {cycle}: 连接确认 {ack}")

            # 发送订阅消息
            subscribe_message = {
                "type": "subscribe",
                "topic": "stock.AAPL.1m"
            }
            await websocket.send(json.dumps(subscribe_message))

            # 等待一段时间
            await asyncio.sleep(1)

            # 发送取消订阅消息
            unsubscribe_message = {
                "type": "unsubscribe",
                "topic": "stock.AAPL.1m"
            }
            await websocket.send(json.dumps(unsubscribe_message))

            # 关闭连接
            await websocket.close()
            logger.info(f"周期 {cycle}: 连接关闭")

            # 周期间隔
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.warning(f"周期 {cycle} 失败: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_websocket_concurrent_operations():
    """测试并发操作"""
    logger.info("测试: 并发操作")

    async def client_task(client_id: str):
        """单个客户端任务"""
        uri = f"{BASE_URL}/{client_id}"
        try:
            async with websockets.connect(uri) as websocket:
                # 等待连接确认
                await websocket.recv()
                logger.info(f"{client_id}: 连接确认")

                # 执行多个操作
                operations = [
                    {"type": "subscribe", "topic": "stock.AAPL.1m"},
                    {"type": "subscribe", "topic": "stock.GOOGL.1m"},
                    {"type": "ping"},
                    {"type": "unsubscribe", "topic": "stock.AAPL.1m"}
                ]

                for op in operations:
                    await websocket.send(json.dumps(op))
                    await asyncio.sleep(0.2)

                # 等待响应
                await asyncio.sleep(1)

                return True
        except Exception as e:
            logger.warning(f"{client_id} 任务失败: {e}")
            return False

    # 并发执行多个客户端任务
    tasks = []
    client_count = 3

    for i in range(client_count):
        client_id = f"concurrent_client_{i}"
        task = asyncio.create_task(client_task(client_id))
        tasks.append(task)

    # 等待所有任务完成
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 统计结果
    successful = sum(1 for result in results if result is True)
    logger.info(f"并发操作结果: {successful}/{client_count} 成功")

    # 至少应该有一半的操作成功
    assert successful >= client_count // 2, f"成功率过低: {successful}/{client_count}"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_websocket_long_running_connection():
    """测试长时间运行的连接"""
    logger.info("测试: 长时间运行的连接")
    client_id = "long_running_client"
    uri = f"{BASE_URL}/{client_id}"

    try:
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            ack = await websocket.recv()
            logger.info(f"连接确认: {ack}")

            # 订阅数据
            subscribe_message = {
                "type": "subscribe",
                "topic": "stock.AAPL.1m"
            }
            await websocket.send(json.dumps(subscribe_message))

            # 保持连接一段时间，定期发送心跳
            duration = 10  # 10秒
            start_time = time.time()

            while time.time() - start_time < duration:
                # 发送心跳
                ping_message = {"type": "ping"}
                await websocket.send(json.dumps(ping_message))

                # 尝试接收消息
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    logger.info(f"收到消息: {response[:100]}...")
                except asyncio.TimeoutError:
                    logger.info("心跳周期内无消息")

                await asyncio.sleep(2)  # 2秒心跳间隔

            logger.info(f"长连接测试完成，持续时间: {duration}秒")

    except Exception as e:
        logger.error(f"长连接测试失败: {e}")
        pytest.fail(f"长连接测试失败: {e}")
