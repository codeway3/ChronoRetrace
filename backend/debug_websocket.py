#!/usr/bin/env python3
"""
调试WebSocket连接问题
"""

import asyncio
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websocket_connection():
    """测试WebSocket连接"""
    BASE_URL = "ws://127.0.0.1:8000/api/v1/ws"
    client_id = "debug_test"
    uri = f"{BASE_URL}/{client_id}"

    try:
        logger.info(f"尝试连接到: {uri}")
        async with websockets.connect(uri) as websocket:
            logger.info("连接成功")

            # 等待连接确认
            ack = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f"连接确认: {ack}")

            # 发送无效JSON
            logger.info("发送无效JSON")
            await websocket.send("这不是有效的JSON")

            # 尝试接收响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                logger.info(f"收到响应: {response}")
            except asyncio.TimeoutError:
                logger.info("没有收到响应（超时）")

    except Exception as e:
        logger.error(f"连接失败: {e}")
        logger.error(f"错误类型: {type(e)}")


if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
