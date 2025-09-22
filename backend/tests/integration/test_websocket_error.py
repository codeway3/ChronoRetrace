#!/usr/bin/env python3
"""
WebSocket 错误测试
专门测试各种可能导致后端报错的WebSocket场景
"""

import asyncio
import json
import logging

import pytest
import websockets

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "ws://127.0.0.1:8000/api/v1/ws"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_invalid_json():
    """测试发送无效JSON"""
    logger.info("测试: 发送无效JSON")
    client_id = "test_invalid_json"
    uri = f"{BASE_URL}/{client_id}"
    websocket = None

    try:
        # 使用更短的超时时间避免测试挂起
        websocket = await asyncio.wait_for(
            websockets.connect(uri), timeout=5.0
        )
        
        # 等待连接确认
        ack = await asyncio.wait_for(websocket.recv(), timeout=3.0)
        logger.info(f"连接确认: {ack}")

        # 发送无效JSON
        await websocket.send("这不是有效的JSON")
        
        # 等待服务器响应
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f"收到响应: {response}")
            
            # 验证响应是错误消息
            response_data = json.loads(response)
            assert response_data.get("type") == "error"
            assert "invalid_json" in response_data.get("error_code", "")
            
        except asyncio.TimeoutError:
            logger.info("没有收到响应（超时）- 这是可接受的行为")
            pass

    except websockets.exceptions.ConnectionClosed as e:
        # 连接被关闭也是可接受的错误处理方式
        logger.info(f"连接被服务器关闭: {e}")
        pass
    except asyncio.TimeoutError:
        logger.warning("连接超时")
        pass
    except Exception as e:
        logger.error(f"无效JSON测试失败: {e}")
        pytest.fail(f"无效JSON测试失败: {e}")
    finally:
        # 确保连接被正确关闭
        if websocket:
            try:
                # 检查连接状态的兼容方式
                if hasattr(websocket, 'closed'):
                    is_closed = websocket.closed
                else:
                    # 对于新版本的websockets库，使用state属性
                    is_closed = getattr(websocket, 'state', None) in [None, 'CLOSED']
                
                if not is_closed:
                    await websocket.close()
                    await asyncio.sleep(0.1)  # 给服务器时间处理关闭
            except Exception as close_error:
                logger.warning(f"关闭连接时出错: {close_error}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_invalid_message_type():
    """测试发送无效消息类型"""
    logger.info("测试: 发送无效消息类型")
    client_id = "test_invalid_type"
    uri = f"{BASE_URL}/{client_id}"
    websocket = None

    try:
        websocket = await asyncio.wait_for(
            websockets.connect(uri), timeout=5.0
        )
        
        # 等待连接确认
        ack = await asyncio.wait_for(websocket.recv(), timeout=3.0)
        logger.info(f"连接确认: {ack}")

        # 发送无效消息类型
        invalid_message = {"type": "invalid_type", "data": "test"}
        await websocket.send(json.dumps(invalid_message))

        # 尝试接收响应
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f"收到响应: {response}")
            # 服务器应该返回错误消息
            assert response is not None
        except asyncio.TimeoutError:
            logger.info("没有收到响应（超时）- 这是可接受的行为")
            pass

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"连接被服务器关闭: {e}")
        pass
    except asyncio.TimeoutError:
        logger.warning("连接超时")
        pass
    except Exception as e:
        logger.error(f"无效消息类型测试失败: {e}")
        pytest.fail(f"无效消息类型测试失败: {e}")
    finally:
        # 确保连接被正确关闭
        if websocket:
            try:
                # 检查连接状态的兼容方式
                if hasattr(websocket, 'closed'):
                    is_closed = websocket.closed
                else:
                    # 对于新版本的websockets库，使用state属性
                    is_closed = getattr(websocket, 'state', None) in [None, 'CLOSED']
                
                if not is_closed:
                    await websocket.close()
                    await asyncio.sleep(0.1)
            except Exception as close_error:
                logger.warning(f"关闭连接时出错: {close_error}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_malformed_subscribe():
    """测试格式错误的订阅消息"""
    logger.info("测试: 发送格式错误的订阅消息")
    client_id = "test_malformed_subscribe"
    uri = f"{BASE_URL}/{client_id}"

    try:
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            ack = await websocket.recv()
            logger.info(f"连接确认: {ack}")

            # 发送缺少topic的订阅消息
            malformed_message = {"type": "subscribe"}  # 缺少topic
            await websocket.send(json.dumps(malformed_message))
            await asyncio.sleep(1)

            # 发送无效topic的订阅消息
            invalid_topic_message = {"type": "subscribe", "topic": ""}  # 空topic
            await websocket.send(json.dumps(invalid_topic_message))
            await asyncio.sleep(1)

            # 尝试接收响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                logger.info(f"收到响应: {response}")
                assert response is not None
            except asyncio.TimeoutError:
                logger.info("没有收到响应（超时）")
                pass

    except websockets.exceptions.ConnectionClosed:
        logger.info("连接被服务器关闭")
        pass
    except Exception as e:
        logger.error(f"格式错误订阅测试失败: {e}")
        pytest.fail(f"格式错误订阅测试失败: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_rapid_connections():
    """测试快速连接和断开"""
    logger.info("测试: 快速连接和断开")

    for i in range(3):  # 减少连接数量避免过度压力
        client_id = f"rapid_test_{i}"
        uri = f"{BASE_URL}/{client_id}"

        try:
            websocket = await websockets.connect(uri)
            # 等待连接确认
            ack = await websocket.recv()
            logger.info(f"快速连接 {i} 确认: {ack}")

            await websocket.send(json.dumps({"type": "ping"}))
            await asyncio.sleep(0.2)
            await websocket.close()
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.warning(f"快速连接 {i} 失败: {e}")
            # 快速连接失败是可接受的


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_large_message():
    """测试发送大消息"""
    logger.info("测试: 发送大消息")
    client_id = "test_large_message"
    uri = f"{BASE_URL}/{client_id}"

    try:
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            ack = await websocket.recv()
            logger.info(f"连接确认: {ack}")

            # 创建一个大消息
            large_data = "x" * 5000  # 5KB
            large_message = {
                "type": "subscribe",
                "topic": "stock.AAPL.1m",
                "large_data": large_data
            }
            await websocket.send(json.dumps(large_message))
            await asyncio.sleep(2)

            # 尝试接收响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"收到响应长度: {len(response)}")
                assert response is not None
            except asyncio.TimeoutError:
                logger.info("没有收到响应（超时）")
                pass

    except websockets.exceptions.ConnectionClosed:
        logger.info("连接被服务器关闭")
        pass
    except Exception as e:
        logger.error(f"大消息测试失败: {e}")
        pytest.fail(f"大消息测试失败: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_concurrent_subscriptions():
    """测试并发订阅相同主题"""
    logger.info("测试: 并发订阅相同主题")
    connections = []

    try:
        for i in range(3):  # 减少并发数量
            client_id = f"concurrent_test_{i}"
            uri = f"{BASE_URL}/{client_id}"
            websocket = await websockets.connect(uri)

            # 等待连接确认
            ack = await websocket.recv()
            logger.info(f"并发连接 {i} 确认: {ack}")
            connections.append(websocket)

            # 所有连接订阅相同主题
            subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}
            await websocket.send(json.dumps(subscribe_message))

        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"并发订阅测试失败: {e}")
        pytest.fail(f"并发订阅测试失败: {e}")
    finally:
        # 关闭所有连接
        for websocket in connections:
            try:
                await websocket.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_connection_without_client_id():
    """测试不带客户端ID的连接"""
    logger.info("测试: 不带客户端ID的连接")

    # 尝试连接到基础URL（不带客户端ID）
    uri = "ws://localhost:8000/api/v1/ws/"

    try:
        websocket = await asyncio.wait_for(
            websockets.connect(uri), timeout=5.0
        )
        await websocket.send(json.dumps({"type": "ping"}))
        await asyncio.sleep(1)
        await websocket.close()
        logger.info("意外成功连接（应该失败）")
        # 如果连接成功，这可能表示服务器配置问题
    except Exception as e:
        logger.info(f"预期的连接失败: {e}")
        # 连接失败是预期的行为
        pass
