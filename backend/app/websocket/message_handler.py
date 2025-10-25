"""
WebSocket消息处理器

负责处理客户端发送的WebSocket消息，包括订阅、取消订阅等操作
"""

import json
import logging
from datetime import datetime
from typing import Any

from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class MessageHandler:
    """WebSocket消息处理器"""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

        # 消息处理器映射
        self.message_handlers = {
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "heartbeat_response": self._handle_heartbeat_response,
            "get_subscriptions": self._handle_get_subscriptions,
            "ping": self._handle_ping,
        }

    async def handle_message(self, client_id: str, message: str) -> None:
        """
        处理客户端消息

        Args:
            client_id: 客户端唯一标识
            message: 客户端发送的消息（JSON字符串）
        """
        try:
            # 解析JSON消息
            data = json.loads(message)

            # 验证消息格式
            if not isinstance(data, dict) or "type" not in data:
                await self._send_error(
                    client_id, "invalid_message_format", "消息格式无效"
                )
                return

            message_type = data["type"]

            # 任何有效消息都视为一次活动，更新最后心跳时间
            if client_id in self.connection_manager.connection_metadata:
                self.connection_manager.connection_metadata[client_id][
                    "last_heartbeat"
                ] = datetime.utcnow()

            # 查找对应的处理器
            handler = self.message_handlers.get(message_type)
            if handler:
                await handler(client_id, data)
            else:
                await self._send_error(
                    client_id, "unknown_message_type", f"未知的消息类型: {message_type}"
                )

        except json.JSONDecodeError:
            await self._send_error(client_id, "invalid_json", "JSON格式错误")
        except Exception as e:
            logger.exception("处理客户端 %s 消息时出错: %s", client_id, e)
            await self._send_error(client_id, "internal_error", "服务器内部错误")

    async def _handle_subscribe(self, client_id: str, data: dict[str, Any]) -> None:
        """
        处理订阅消息

        Args:
            client_id: 客户端唯一标识
            data: 消息数据
        """
        try:
            topic = data.get("topic")
            if not topic:
                await self._send_error(client_id, "missing_topic", "缺少订阅主题")
                return

            # 验证主题格式
            if not self._validate_topic(topic):
                await self._send_error(
                    client_id, "invalid_topic", f"无效的主题格式: {topic}"
                )
                return

            # 执行订阅
            success = await self.connection_manager.subscribe(client_id, topic)

            if not success:
                await self._send_error(
                    client_id, "subscribe_failed", f"订阅主题失败: {topic}"
                )

        except Exception as e:
            logger.exception("处理订阅消息时出错: %s", e)
            await self._send_error(client_id, "subscribe_error", "订阅处理错误")

    async def _handle_unsubscribe(self, client_id: str, data: dict[str, Any]) -> None:
        """
        处理取消订阅消息

        Args:
            client_id: 客户端唯一标识
            data: 消息数据
        """
        try:
            topic = data.get("topic")
            if not topic:
                await self._send_error(client_id, "missing_topic", "缺少取消订阅主题")
                return

            # 执行取消订阅
            success = await self.connection_manager.unsubscribe(client_id, topic)

            if not success:
                await self._send_error(
                    client_id, "unsubscribe_failed", f"取消订阅主题失败: {topic}"
                )

        except Exception as e:
            logger.exception("处理取消订阅消息时出错: %s", e)
            await self._send_error(client_id, "unsubscribe_error", "取消订阅处理错误")

    async def _handle_heartbeat_response(
        self, client_id: str, data: dict[str, Any]
    ) -> None:
        """
        处理心跳响应消息

        Args:
            client_id: 客户端唯一标识
            data: 消息数据
        """
        try:
            # 更新客户端最后活跃时间
            if client_id in self.connection_manager.connection_metadata:
                self.connection_manager.connection_metadata[client_id][
                    "last_heartbeat"
                ] = datetime.utcnow()

            logger.debug(f"收到客户端 {client_id} 的心跳响应")

        except Exception as e:
            logger.exception("处理心跳响应时出错: %s", e)

    async def _handle_get_subscriptions(
        self, client_id: str, data: dict[str, Any]
    ) -> None:
        """
        处理获取订阅列表消息

        Args:
            client_id: 客户端唯一标识
            data: 消息数据
        """
        try:
            subscriptions = list(
                self.connection_manager.client_subscriptions.get(client_id, set())
            )

            await self.connection_manager.send_to_client(
                client_id,
                {
                    "type": "subscriptions_list",
                    "subscriptions": subscriptions,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.exception("处理获取订阅列表时出错: %s", e)
            await self._send_error(
                client_id, "get_subscriptions_error", "获取订阅列表错误"
            )

    async def _handle_ping(self, client_id: str, data: dict[str, Any]) -> None:
        """
        处理ping消息

        Args:
            client_id: 客户端唯一标识
            data: 消息数据
        """
        try:
            # 将 ping 视为一次心跳，更新最后活跃时间，避免被误判为不活跃
            if client_id in self.connection_manager.connection_metadata:
                self.connection_manager.connection_metadata[client_id][
                    "last_heartbeat"
                ] = datetime.utcnow()

            await self.connection_manager.send_to_client(
                client_id, {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
            )

        except Exception as e:
            logger.exception("处理ping消息时出错: %s", e)

    def _validate_topic(self, topic: str) -> bool:
        """
        验证主题格式

        Args:
            topic: 主题名称

        Returns:
            bool: 主题格式是否有效
        """
        try:
            # 主题格式: type.symbol.interval 或 type.market.summary
            parts = topic.split(".")

            if len(parts) < 2:
                return False

            topic_type = parts[0]

            # 支持的主题类型
            valid_types = [
                "stock",
                "crypto",
                "futures",
                "options",
                "commodity",
                "market",
            ]

            if topic_type not in valid_types:
                return False

            # 市场概览主题格式: market.{market}.summary
            if topic_type == "market":
                return len(parts) == 3 and parts[2] == "summary"

            # 其他主题格式: {type}.{symbol}.{interval}
            if len(parts) != 3:
                return False

            symbol = parts[1]
            interval = parts[2]

            # 验证符号（基本验证，不为空且长度合理）
            if not symbol or len(symbol) > 20:
                return False

            # 验证时间间隔
            valid_intervals = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
            return interval in valid_intervals

        except Exception:
            return False

    async def _send_error(
        self, client_id: str, error_code: str, error_message: str
    ) -> None:
        """
        向客户端发送错误消息

        Args:
            client_id: 客户端唯一标识
            error_code: 错误代码
            error_message: 错误消息
        """
        try:
            await self.connection_manager.send_to_client(
                client_id,
                {
                    "type": "error",
                    "error_code": error_code,
                    "error_message": error_message,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.exception(f"发送错误消息失败: {e}")

    def get_supported_message_types(self) -> list:
        """
        获取支持的消息类型列表

        Returns:
            list: 支持的消息类型
        """
        return list(self.message_handlers.keys())

    def get_topic_examples(self) -> dict[str, list]:
        """
        获取主题示例

        Returns:
            Dict: 按类型分组的主题示例
        """
        return {
            "stock": ["stock.AAPL.1m", "stock.TSLA.5m", "stock.MSFT.1h"],
            "crypto": ["crypto.BTCUSDT.1m", "crypto.ETHUSDT.5m"],
            "futures": ["futures.ES.1m", "futures.NQ.5m"],
            "market": ["market.US.summary", "market.CN.summary"],
        }
