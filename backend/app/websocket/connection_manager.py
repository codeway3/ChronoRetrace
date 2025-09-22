"""
WebSocket连接管理器

负责管理WebSocket连接的生命周期、订阅管理和消息分发
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 活跃连接: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # 订阅关系: topic -> set of client_ids
        self.subscriptions: Dict[str, Set[str]] = {}

        # 客户端订阅: client_id -> set of topics
        self.client_subscriptions: Dict[str, Set[str]] = {}

        # 连接元数据
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # 心跳任务
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def connect(
        self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None
    ) -> bool:
        """
        建立WebSocket连接

        Args:
            websocket: WebSocket连接对象
            client_id: 客户端唯一标识
            user_id: 用户ID（可选）

        Returns:
            bool: 连接是否成功建立
        """
        try:
            await websocket.accept()

            # 如果客户端已存在，先断开旧连接
            if client_id in self.active_connections:
                await self.disconnect(client_id)

            # 保存连接
            self.active_connections[client_id] = websocket
            self.client_subscriptions[client_id] = set()

            # 保存连接元数据
            self.connection_metadata[client_id] = {
                "user_id": user_id,
                "connected_at": datetime.utcnow(),
                "last_heartbeat": datetime.utcnow(),
            }

            # 启动心跳检测
            self.heartbeat_tasks[client_id] = asyncio.create_task(
                self._heartbeat_monitor(client_id)
            )

            logger.info(f"客户端 {client_id} 连接成功，用户ID: {user_id}")

            # 发送连接确认消息
            await self.send_to_client(
                client_id,
                {
                    "type": "connection_ack",
                    "client_id": client_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            return True

        except Exception as e:
            logger.error(f"客户端 {client_id} 连接失败: {e}")
            return False

    async def disconnect(self, client_id: str) -> None:
        """
        断开客户端连接

        Args:
            client_id: 客户端唯一标识
        """
        try:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]

                # 尝试优雅关闭WebSocket连接
                try:
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.close(code=1000, reason="Server disconnect")
                        logger.debug(f"客户端 {client_id} WebSocket连接已优雅关闭")
                except Exception as close_error:
                    logger.warning(
                        f"关闭客户端 {client_id} WebSocket连接时出错: {close_error}"
                    )

                # 使用内部清理方法
                await self._cleanup_connection(client_id)

                logger.info(f"客户端 {client_id} 连接已断开")
            else:
                logger.debug(f"客户端 {client_id} 不在活跃连接列表中")

        except Exception as e:
            logger.error(f"断开客户端 {client_id} 连接时出错: {e}")
            # 即使出错也要尝试清理
            try:
                await self._cleanup_connection(client_id)
            except Exception as cleanup_error:
                logger.error(f"强制清理客户端 {client_id} 连接时出错: {cleanup_error}")

    async def subscribe(self, client_id: str, topic: str) -> bool:
        """
        订阅主题

        Args:
            client_id: 客户端唯一标识
            topic: 订阅主题

        Returns:
            bool: 订阅是否成功
        """
        try:
            if client_id not in self.active_connections:
                logger.warning(f"客户端 {client_id} 不存在，无法订阅主题 {topic}")
                return False

            # 添加到订阅关系
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(client_id)

            # 添加到客户端订阅列表
            self.client_subscriptions[client_id].add(topic)

            logger.info(f"客户端 {client_id} 订阅主题 {topic}")

            # 发送订阅确认
            await self.send_to_client(
                client_id,
                {
                    "type": "subscribe_ack",
                    "topic": topic,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            return True

        except Exception as e:
            logger.error(f"客户端 {client_id} 订阅主题 {topic} 失败: {e}")
            return False

    async def unsubscribe(self, client_id: str, topic: str) -> bool:
        """
        取消订阅主题

        Args:
            client_id: 客户端唯一标识
            topic: 取消订阅的主题

        Returns:
            bool: 取消订阅是否成功
        """
        try:
            # 从订阅关系中移除
            if topic in self.subscriptions:
                self.subscriptions[topic].discard(client_id)
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]

            # 从客户端订阅列表中移除
            if client_id in self.client_subscriptions:
                self.client_subscriptions[client_id].discard(topic)

            logger.info(f"客户端 {client_id} 取消订阅主题 {topic}")

            # 发送取消订阅确认
            if client_id in self.active_connections:
                await self.send_to_client(
                    client_id,
                    {
                        "type": "unsubscribe_ack",
                        "topic": topic,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            return True

        except Exception as e:
            logger.error(f"客户端 {client_id} 取消订阅主题 {topic} 失败: {e}")
            return False

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        向指定客户端发送消息

        Args:
            client_id: 客户端唯一标识
            message: 要发送的消息

        Returns:
            bool: 消息是否发送成功
        """
        try:
            if client_id not in self.active_connections:
                logger.debug(f"客户端 {client_id} 不在活跃连接列表中")
                return False

            websocket = self.active_connections[client_id]

            # 检查WebSocket连接状态
            if websocket.client_state.name != "CONNECTED":
                logger.warning(
                    f"客户端 {client_id} WebSocket状态异常: {websocket.client_state.name}"
                )
                await self._cleanup_connection(client_id)
                return False

            # 发送消息
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            return True

        except WebSocketDisconnect:
            logger.info(f"客户端 {client_id} 连接已断开")
            await self._cleanup_connection(client_id)
            return False
        except ConnectionResetError:
            logger.info(f"客户端 {client_id} 连接被重置")
            await self._cleanup_connection(client_id)
            return False
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"向客户端 {client_id} 发送消息失败: {e}")

            # 检查是否是连接相关的错误
            connection_errors = [
                "not connected",
                "closed",
                "connection",
                "broken pipe",
                "connection reset",
                "websocket is not connected",
            ]

            if any(err in error_msg for err in connection_errors):
                logger.info(f"检测到客户端 {client_id} 连接问题，清理连接")
                await self._cleanup_connection(client_id)

            return False

    async def _cleanup_connection(self, client_id: str) -> None:
        """
        清理连接的内部方法，避免重复调用disconnect

        Args:
            client_id: 客户端唯一标识
        """
        try:
            # 取消心跳任务
            if client_id in self.heartbeat_tasks:
                self.heartbeat_tasks[client_id].cancel()
                del self.heartbeat_tasks[client_id]

            # 清理订阅关系
            if client_id in self.client_subscriptions:
                for topic in self.client_subscriptions[client_id].copy():
                    if topic in self.subscriptions:
                        self.subscriptions[topic].discard(client_id)
                        if not self.subscriptions[topic]:
                            del self.subscriptions[topic]
                del self.client_subscriptions[client_id]

            # 移除连接
            if client_id in self.active_connections:
                del self.active_connections[client_id]

            # 清理元数据
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]

            logger.debug(f"客户端 {client_id} 连接清理完成")

        except Exception as e:
            logger.error(f"清理客户端 {client_id} 连接时出错: {e}")

    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]) -> int:
        """
        向订阅指定主题的所有客户端广播消息

        Args:
            topic: 主题名称
            message: 要广播的消息

        Returns:
            int: 成功发送的客户端数量
        """
        if topic not in self.subscriptions:
            return 0

        # 添加主题信息到消息
        message["topic"] = topic
        message["timestamp"] = datetime.utcnow().isoformat()

        success_count = 0
        failed_clients = []

        # 并发发送消息
        tasks = []
        client_ids = list(self.subscriptions[topic])

        for client_id in client_ids:
            task = asyncio.create_task(self.send_to_client(client_id, message))
            tasks.append((client_id, task))

        # 等待所有发送任务完成
        for client_id, task in tasks:
            try:
                success = await task
                if success:
                    success_count += 1
                else:
                    failed_clients.append(client_id)
            except Exception as e:
                logger.error(f"向客户端 {client_id} 广播消息失败: {e}")
                failed_clients.append(client_id)

        # 清理失败的连接
        for client_id in failed_clients:
            await self.disconnect(client_id)

        if success_count > 0:
            logger.debug(
                f"向主题 {topic} 广播消息，成功: {success_count}, 失败: {len(failed_clients)}"
            )

        return success_count

    async def _heartbeat_monitor(self, client_id: str) -> None:
        """
        心跳监控任务

        Args:
            client_id: 客户端唯一标识
        """
        try:
            while client_id in self.active_connections:
                await asyncio.sleep(30)  # 每30秒发送一次心跳

                # 双重检查连接是否还存在
                if client_id not in self.active_connections:
                    logger.debug(f"客户端 {client_id} 已从活跃连接中移除，停止心跳")
                    break

                # 检查WebSocket连接状态
                websocket = self.active_connections.get(client_id)
                if not websocket:
                    logger.debug(f"客户端 {client_id} WebSocket对象不存在，停止心跳")
                    break

                if websocket.client_state.name != "CONNECTED":
                    logger.info(
                        f"客户端 {client_id} WebSocket状态异常: {websocket.client_state.name}，停止心跳"
                    )
                    await self._cleanup_connection(client_id)
                    break

                try:
                    # 发送心跳消息
                    heartbeat_message = {
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat(),
                        "client_id": client_id,
                    }

                    await websocket.send_text(
                        json.dumps(heartbeat_message, ensure_ascii=False)
                    )

                    # 更新最后心跳时间
                    if client_id in self.connection_metadata:
                        self.connection_metadata[client_id][
                            "last_heartbeat"
                        ] = datetime.utcnow()

                    logger.debug(f"向客户端 {client_id} 发送心跳")

                except WebSocketDisconnect:
                    logger.info(f"心跳检测到客户端 {client_id} 已断开连接")
                    await self._cleanup_connection(client_id)
                    break
                except ConnectionResetError:
                    logger.info(f"心跳检测到客户端 {client_id} 连接被重置")
                    await self._cleanup_connection(client_id)
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.error(f"向客户端 {client_id} 发送心跳失败: {e}")

                    # 检查是否是连接相关的错误
                    connection_errors = [
                        "not connected",
                        "closed",
                        "connection",
                        "broken pipe",
                        "connection reset",
                        "websocket is not connected",
                    ]

                    if any(err in error_msg for err in connection_errors):
                        logger.info(f"心跳检测到客户端 {client_id} 连接问题，清理连接")
                        await self._cleanup_connection(client_id)
                    break

        except asyncio.CancelledError:
            logger.debug(f"客户端 {client_id} 心跳监控任务被取消")
        except Exception as e:
            logger.error(f"客户端 {client_id} 心跳监控出错: {e}")
        finally:
            # 清理心跳任务记录
            if client_id in self.heartbeat_tasks:
                del self.heartbeat_tasks[client_id]
            logger.debug(f"客户端 {client_id} 心跳监控任务结束")

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息

        Returns:
            Dict: 连接统计信息
        """
        return {
            "total_connections": len(self.active_connections),
            "total_subscriptions": sum(
                len(clients) for clients in self.subscriptions.values()
            ),
            "topics_count": len(self.subscriptions),
            "connections": {
                client_id: {
                    "subscriptions": list(
                        self.client_subscriptions.get(client_id, set())
                    ),
                    "metadata": self.connection_metadata.get(client_id, {}),
                }
                for client_id in self.active_connections
            },
        }

    def get_topic_subscribers(self, topic: str) -> Set[str]:
        """
        获取主题的订阅者列表

        Args:
            topic: 主题名称

        Returns:
            Set[str]: 订阅者客户端ID集合
        """
        return self.subscriptions.get(topic, set()).copy()

    async def cleanup_inactive_connections(self, timeout_minutes: int = 5) -> int:
        """
        清理不活跃的连接

        Args:
            timeout_minutes: 超时时间（分钟）

        Returns:
            int: 清理的连接数量
        """
        current_time = datetime.utcnow()
        inactive_clients = []

        for client_id, metadata in self.connection_metadata.items():
            last_heartbeat = metadata.get("last_heartbeat")
            if last_heartbeat:
                time_diff = (current_time - last_heartbeat).total_seconds() / 60
                if time_diff > timeout_minutes:
                    inactive_clients.append(client_id)

        # 断开不活跃的连接
        for client_id in inactive_clients:
            await self.disconnect(client_id)

        if inactive_clients:
            logger.info(f"清理了 {len(inactive_clients)} 个不活跃的连接")

        return len(inactive_clients)
