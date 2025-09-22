#!/usr/bin/env python3
"""
WebSocket基础功能测试
测试连接、订阅、取消订阅等基本功能
"""

import asyncio
import json
import websockets
import websockets.exceptions
import pytest
import sys


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_subscription():
    client_id = "test_client_001"
    uri = f"ws://localhost:8000/api/v1/ws/{client_id}"

    try:
        print(f"正在连接到 {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功!")

            # 发送订阅消息 (正确格式: type.symbol.interval)
            subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}

            print(f"发送订阅消息: {json.dumps(subscribe_message, ensure_ascii=False)}")
            await websocket.send(json.dumps(subscribe_message))

            # 监听消息
            print("等待服务器响应...")
            timeout_count = 0
            max_timeout = 5  # 最多等待5次
            received_subscribe_ack = False

            while timeout_count < max_timeout:
                try:
                    # 等待消息，超时时间为3秒
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    print(f"收到消息: {message}")

                    # 尝试解析JSON
                    try:
                        data = json.loads(message)
                        print(
                            f"解析后的数据: {json.dumps(data, ensure_ascii=False, indent=2)}"
                        )

                        # 检查是否收到订阅确认
                        if data.get("type") == "subscribe_ack":
                            received_subscribe_ack = True
                            print("✅ 收到订阅确认，测试成功")
                            break

                    except json.JSONDecodeError:
                        print(f"非JSON消息: {message}")

                    timeout_count = 0  # 重置超时计数

                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"等待消息超时 ({timeout_count}/{max_timeout})")

                    if timeout_count >= max_timeout:
                        print("达到最大等待时间，结束测试")
                        break
                except websockets.exceptions.ConnectionClosed:
                    print("连接已关闭，结束监听")
                    break

            # 只有在收到订阅确认后才发送取消订阅消息
            if received_subscribe_ack:
                unsubscribe_message = {"type": "unsubscribe", "topic": "stock.AAPL.1m"}

                print(
                    f"发送取消订阅消息: {json.dumps(unsubscribe_message, ensure_ascii=False)}"
                )
                await websocket.send(json.dumps(unsubscribe_message))

                # 等待最后的响应
                try:
                    final_message = await asyncio.wait_for(
                        websocket.recv(), timeout=2.0
                    )
                    print(f"最终消息: {final_message}")
                except asyncio.TimeoutError:
                    print("未收到最终响应")

            print("✅ WebSocket测试完成")

    except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError):
        print("❌ 连接被拒绝，请确保后端服务正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

    return received_subscribe_ack


@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_connection_only():
    """仅测试WebSocket连接"""
    client_id = "test_client_connection"
    uri = f"ws://localhost:8000/api/v1/ws/{client_id}"

    try:
        print(f"测试连接到 {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接测试成功!")

            # 发送ping消息
            await websocket.send("ping")
            print("发送了ping消息")

            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"收到响应: {response}")
            except asyncio.TimeoutError:
                print("未收到响应（这是正常的，因为服务器可能不处理ping消息）")

            return True

    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


if __name__ == "__main__":
    print("=== WebSocket测试开始 ===")

    # 首先测试基本连接
    print("\n1. 测试基本连接...")
    connection_result = asyncio.run(test_websocket_connection_only())

    if connection_result:
        print("\n2. 测试完整功能...")
        full_test_result = asyncio.run(test_websocket_subscription())

        if full_test_result:
            print("\n🎉 所有测试通过!")
            sys.exit(0)
        else:
            print("\n⚠️ 功能测试失败")
            sys.exit(1)
    else:
        print("\n❌ 连接测试失败")
        sys.exit(1)
