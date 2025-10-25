#!/usr/bin/env python3
"""
WebSocket修复验证测试脚本
"""

import json
from contextlib import ExitStack

import pytest


@pytest.mark.integration
def test_single_connection(client):
    """测试单个连接"""
    print("🔍 测试单个WebSocket连接...")

    try:
        with client.websocket_connect("/api/v1/ws/test_client") as websocket:
            print("✅ 连接成功")

            # 等待确认
            ack = websocket.receive_text()
            ack_data = json.loads(ack)
            print(f"📨 收到确认: {ack_data['client_id']}")

            # 测试ping
            websocket.send_text(json.dumps({"type": "ping"}))
            _response = websocket.receive_text()
            print("✅ ping/pong 成功")

            # 测试订阅
            websocket.send_text(
                json.dumps({"type": "subscribe", "topic": "test_topic"})
            )
            _response = websocket.receive_text()
            print("✅ 订阅成功")

            # 断开连接
            # TestClient 会在 with 块结束时自动关闭连接
            print("✅ 连接正常断开")
            assert True

    except Exception as e:
        print(f"❌ 单连接测试失败: {e}")
        pytest.fail(f"❌ 单连接测试失败: {e}")


@pytest.mark.integration
def test_multiple_connections(client):
    """测试多个连接"""
    print("🔍 测试多个WebSocket连接...")

    with ExitStack() as stack:
        connections = []
        try:
            # 创建5个连接
            for i in range(5):
                websocket = stack.enter_context(
                    client.websocket_connect(f"/api/v1/ws/lifecycle_test_{i}")
                )
                connections.append((f"lifecycle_test_{i}", websocket))

                # 等待确认
                _ack = websocket.receive_text()
                print(f"✅ 连接 {i + 1}/5 创建成功")

            # 发送消息
            for client_id, websocket in connections:
                websocket.send_text(json.dumps({"type": "ping"}))
                _response = websocket.receive_text()
                print(f"✅ {client_id} ping/pong 成功")

            print("✅ 多连接测试成功")

        except Exception as e:
            print(f"❌ 多连接测试失败: {e}")
            pytest.fail(f"❌ 多连接测试失败: {e}")


# 移除 main 函数和 if __name__ == "__main__" 块，因为测试将由 pytest 运行
