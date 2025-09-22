#!/usr/bin/env python3
"""
WebSocket订阅功能测试
专门测试订阅和取消订阅功能
"""

import asyncio
import json
import websockets
import pytest
from datetime import datetime


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscription():
    """测试WebSocket订阅功能"""
    client_id = "test_subscription_client"
    uri = f"ws://localhost:8000/api/v1/ws/{client_id}"

    print(f"=== WebSocket订阅测试开始 ===")
    print(f"连接到: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功!")

            # 等待连接确认
            response = await websocket.recv()
            print(f"收到连接确认: {response}")

            # 发送订阅消息 (正确格式: type.symbol.interval)
            subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}

            print(f"发送订阅消息: {json.dumps(subscribe_message, ensure_ascii=False)}")
            await websocket.send(json.dumps(subscribe_message))

            # 等待订阅确认
            response = await websocket.recv()
            print(f"收到订阅确认: {response}")

            # 监听消息一段时间
            print("监听消息中...")
            timeout_count = 0
            max_timeouts = 5

            while timeout_count < max_timeouts:
                try:
                    # 等待消息，超时时间5秒
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"收到消息: {json.dumps(data, ensure_ascii=False, indent=2)}")

                    # 重置超时计数
                    timeout_count = 0

                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"等待消息超时 ({timeout_count}/{max_timeouts})")

            # 发送取消订阅消息
            unsubscribe_message = {"type": "unsubscribe", "topic": "stock.AAPL.1m"}

            print(
                f"发送取消订阅消息: {json.dumps(unsubscribe_message, ensure_ascii=False)}"
            )
            await websocket.send(json.dumps(unsubscribe_message))

            # 等待取消订阅确认
            response = await websocket.recv()
            print(f"收到取消订阅确认: {response}")

            print("✅ 订阅测试完成")
            return True

    except Exception as e:
        print(f"❌ 订阅测试失败: {e}")
        return False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ping():
    """测试ping功能"""
    client_id = "test_ping_client"
    uri = f"ws://localhost:8000/api/v1/ws/{client_id}"

    print(f"\n=== Ping测试开始 ===")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功!")

            # 等待连接确认
            await websocket.recv()

            # 发送ping消息
            ping_message = {"type": "ping"}
            print(f"发送ping消息: {json.dumps(ping_message)}")
            await websocket.send(json.dumps(ping_message))

            # 等待pong响应
            response = await websocket.recv()
            print(f"收到pong响应: {response}")

            print("✅ Ping测试完成")
            return True

    except Exception as e:
        print(f"❌ Ping测试失败: {e}")
        return False


if __name__ == "__main__":
    print(f"开始时间: {datetime.now()}")

    # 运行订阅测试
    subscription_result = asyncio.run(test_subscription())

    # 运行ping测试
    ping_result = asyncio.run(test_ping())

    print(f"\n=== 测试结果 ===")
    print(f"订阅测试: {'✅ 通过' if subscription_result else '❌ 失败'}")
    print(f"Ping测试: {'✅ 通过' if ping_result else '❌ 失败'}")
    print(f"结束时间: {datetime.now()}")
