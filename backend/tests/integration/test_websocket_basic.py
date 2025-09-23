#!/usr/bin/env python3
"""
WebSocket基础功能测试
测试连接、订阅、取消订阅等基本功能
"""

import json
import pytest
import sys


@pytest.mark.integration
def test_websocket_subscription(client):
    client_id = "test_client_001"

    try:
        print(f"正在连接...")
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            print("✅ WebSocket连接成功!")

            # 1. 接收连接确认
            conn_ack_msg = websocket.receive_text()
            print(f"收到连接确认: {conn_ack_msg}")

            # 2. 发送订阅消息
            subscribe_message = {"type": "subscribe", "topic": "stock.AAPL.1m"}
            print(f"发送订阅消息: {json.dumps(subscribe_message, ensure_ascii=False)}")
            websocket.send_text(json.dumps(subscribe_message))

            # 3. 接收订阅确认
            sub_ack_msg = websocket.receive_text()
            print(f"收到订阅确认: {sub_ack_msg}")

            received_subscribe_ack = False
            try:
                data = json.loads(sub_ack_msg)
                if data.get("type") == "subscribe_ack":
                    received_subscribe_ack = True
                    print("✅ 收到订阅确认")
            except json.JSONDecodeError:
                print(f"非JSON消息: {sub_ack_msg}")

            assert received_subscribe_ack, "未收到订阅确认"

            # 4. 取消订阅
            unsubscribe_message = {"type": "unsubscribe", "topic": "stock.AAPL.1m"}
            print(
                f"发送取消订阅消息: {json.dumps(unsubscribe_message, ensure_ascii=False)}"
            )
            websocket.send_text(json.dumps(unsubscribe_message))

            # 5. 接收取消订阅确认
            unsub_ack_msg = websocket.receive_text()
            print(f"收到取消订阅确认: {unsub_ack_msg}")

            received_unsubscribe_ack = False
            try:
                data = json.loads(unsub_ack_msg)
                if data.get("type") == "unsubscribe_ack":
                    received_unsubscribe_ack = True
                    print("✅ 收到取消订阅确认")
            except json.JSONDecodeError:
                print(f"非JSON消息: {unsub_ack_msg}")

            assert received_unsubscribe_ack, "未收到取消订阅确认"

            print("✅ WebSocket测试完成")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        pytest.fail(f"❌ 测试失败: {e}")


@pytest.mark.integration
def test_websocket_connection_only(client):
    """仅测试WebSocket连接"""
    client_id = "test_client_connection"

    try:
        print(f"测试连接...")
        with client.websocket_connect(f"/api/v1/ws/{client_id}") as websocket:
            print("✅ WebSocket连接测试成功!")

            # 发送ping消息
            websocket.send_text("ping")
            print("发送了ping消息")

            # 等待响应
            try:
                response = websocket.receive_text()
                print(f"收到响应: {response}")
            except Exception:
                print("未收到响应（这是正常的，因为服务器可能不处理ping消息）")

    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        pytest.fail(f"❌ 连接测试失败: {e}")


if __name__ == "__main__":
    print("此脚本现在应通过 pytest 运行")
    sys.exit(1)
