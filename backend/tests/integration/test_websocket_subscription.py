#!/usr/bin/env python3
"""
WebSocket订阅功能测试
专门测试订阅和取消订阅功能
"""

import json

import pytest


@pytest.mark.integration
def test_subscription(client):
    """测试WebSocket订阅功能"""
    client_id = "test_subscription_client"

    print("=== WebSocket订阅测试开始 ===")

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            print("✅ WebSocket连接成功!")

            # 1. 接收连接确认
            response = websocket.receive_text()
            print(f"收到连接确认: {response}")

            # 2. 发送订阅消息
            subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}
            print(f"发送订阅消息: {json.dumps(subscribe_message, ensure_ascii=False)}")
            websocket.send_text(json.dumps(subscribe_message))

            # 3. 接收订阅确认
            sub_ack_msg = websocket.receive_text()
            print(f"收到订阅确认: {sub_ack_msg}")
            sub_ack_data = json.loads(sub_ack_msg)
            assert sub_ack_data.get("type") == "subscribe_ack"

            # 4. 发送取消订阅消息
            unsubscribe_message = {"type": "unsubscribe", "topic": "stock.AAPL.1m"}
            print(
                f"发送取消订阅消息: {json.dumps(unsubscribe_message, ensure_ascii=False)}"
            )
            websocket.send_text(json.dumps(unsubscribe_message))

            # 5. 接收取消订阅确认
            unsub_ack_msg = websocket.receive_text()
            print(f"收到取消订阅确认: {unsub_ack_msg}")
            unsub_ack_data = json.loads(unsub_ack_msg)
            assert unsub_ack_data.get("type") == "unsubscribe_ack"

            print("✅ 订阅测试完成")

    except Exception as e:
        print(f"❌ 订阅测试失败: {e}")
        pytest.fail(f"订阅测试失败: {e}")


@pytest.mark.integration
def test_ping(client):
    """测试ping功能"""
    client_id = "test_ping_client"

    print("\n=== Ping测试开始 ===")

    try:
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            print("✅ WebSocket连接成功!")

            # 等待连接确认
            websocket.receive_text()

            # 发送ping消息
            ping_message = {"type": "ping"}
            print(f"发送ping消息: {json.dumps(ping_message)}")
            websocket.send_text(json.dumps(ping_message))

            # 等待pong响应
            response = websocket.receive_text()
            print(f"收到pong响应: {response}")

            print("✅ Ping测试完成")
            assert True

    except Exception as e:
        print(f"❌ Ping测试失败: {e}")
        pytest.fail(f"Ping测试失败: {e}")
