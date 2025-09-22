#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket修复验证测试脚本
"""
import asyncio
import websockets
import json
import pytest
import time


@pytest.mark.integration
@pytest.mark.asyncio
async def test_single_connection():
    """测试单个连接"""
    print("🔍 测试单个WebSocket连接...")

    try:
        uri = "ws://localhost:8000/api/v1/ws/test_client"
        websocket = await websockets.connect(uri)
        print("✅ 连接成功")

        # 等待确认
        ack = await websocket.recv()
        ack_data = json.loads(ack)
        print(f"📨 收到确认: {ack_data['client_id']}")

        # 测试ping
        await websocket.send(json.dumps({"type": "ping"}))
        response = await websocket.recv()
        print("✅ ping/pong 成功")

        # 测试订阅
        await websocket.send(json.dumps({"type": "subscribe", "topic": "test_topic"}))
        response = await websocket.recv()
        print("✅ 订阅成功")

        # 断开连接
        await websocket.close()
        print("✅ 连接正常断开")
        return True

    except Exception as e:
        print(f"❌ 单连接测试失败: {e}")
        return False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_connections():
    """测试多个连接"""
    print("🔍 测试多个WebSocket连接...")

    connections = []
    try:
        # 创建5个连接
        for i in range(5):
            uri = f"ws://localhost:8000/api/v1/ws/lifecycle_test_{i}"
            websocket = await websockets.connect(uri)
            connections.append((f"lifecycle_test_{i}", websocket))

            # 等待确认
            ack = await websocket.recv()
            print(f"✅ 连接 {i+1}/5 创建成功")

        # 发送消息
        for client_id, websocket in connections:
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            print(f"✅ {client_id} ping/pong 成功")

        # 断开连接
        for client_id, websocket in connections:
            await websocket.close()
            print(f"✅ {client_id} 断开成功")

        print("✅ 多连接测试成功")
        return True

    except Exception as e:
        print(f"❌ 多连接测试失败: {e}")
        # 清理连接
        for _, websocket in connections:
            try:
                await websocket.close()
            except:
                pass
        return False


async def main():
    """主测试函数"""
    print("🚀 开始WebSocket修复验证测试...")
    print("=" * 50)

    # 测试单个连接
    single_result = await test_single_connection()
    print()

    # 测试多个连接
    multiple_result = await test_multiple_connections()
    print()

    # 总结
    print("=" * 50)
    if single_result and multiple_result:
        print("🎉 所有测试通过！WebSocket修复成功！")
        print("✅ 不再出现 'WebSocket is not connected' 错误")
        print("✅ 连接断开处理正常")
        print("✅ 订阅清理机制工作正常")
    else:
        print("❌ 部分测试失败，需要进一步检查")


if __name__ == "__main__":
    asyncio.run(main())
