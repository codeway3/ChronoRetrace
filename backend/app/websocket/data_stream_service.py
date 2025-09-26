"""
实时数据流服务

负责从数据源获取实时数据并通过WebSocket推送给订阅的客户端
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from ..data.managers.data_manager import fetch_stock_data
from ..infrastructure.cache.redis_manager import RedisCacheManager
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class DataStreamService:
    """实时数据流服务"""

    def __init__(
        self, connection_manager: ConnectionManager, redis_manager: RedisCacheManager
    ):
        self.connection_manager = connection_manager
        self.redis_manager = redis_manager

        # 活跃的数据流: topic -> task
        self.active_streams: dict[str, asyncio.Task] = {}

        # 数据流配置
        self.stream_configs: dict[str, dict[str, Any]] = {}

        # 最后推送的数据: topic -> data
        self.last_data: dict[str, dict[str, Any]] = {}

        # 数据流统计
        self.stream_stats: dict[str, dict[str, Any]] = {}

        # 清理任务（将在start方法中启动）
        self.cleanup_task = None

    async def start(self) -> None:
        """
        启动数据流服务
        """
        try:
            self._running = True
            # 启动清理任务
            self.cleanup_task = asyncio.create_task(self._cleanup_inactive_streams())
            logger.info("数据流服务启动成功")
        except Exception as e:
            logger.error(f"启动数据流服务失败: {e}")
            raise

    async def stop(self) -> None:
        """
        停止数据流服务
        """
        try:
            self._running = False

            # 停止所有活跃的数据流
            for topic in list(self.active_streams.keys()):
                await self.stop_data_stream(topic)

            # 停止清理任务
            if self.cleanup_task and not self.cleanup_task.done():
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass

            logger.info("数据流服务停止成功")
        except Exception as e:
            logger.error(f"停止数据流服务失败: {e}")

    async def start_data_stream(self, topic: str) -> bool:
        """
        启动数据流

        Args:
            topic: 数据流主题

        Returns:
            bool: 启动是否成功
        """
        try:
            if topic in self.active_streams:
                logger.debug(f"数据流 {topic} 已经在运行")
                return True

            # 解析主题
            topic_info = self._parse_topic(topic)
            if not topic_info:
                logger.error(f"无效的主题格式: {topic}")
                return False

            # 创建数据流任务
            stream_task = asyncio.create_task(
                self._data_stream_worker(topic, topic_info)
            )
            self.active_streams[topic] = stream_task

            # 保存配置
            self.stream_configs[topic] = topic_info

            # 初始化统计
            self.stream_stats[topic] = {
                "started_at": datetime.utcnow(),
                "messages_sent": 0,
                "last_update": None,
                "errors": 0,
            }

            logger.info(f"启动数据流: {topic}")
            return True

        except Exception as e:
            logger.error(f"启动数据流 {topic} 失败: {e}")
            return False

    async def stop_data_stream(self, topic: str) -> bool:
        """
        停止数据流

        Args:
            topic: 数据流主题

        Returns:
            bool: 停止是否成功
        """
        try:
            if topic not in self.active_streams:
                logger.debug(f"数据流 {topic} 不存在")
                return True

            # 取消任务
            task = self.active_streams[topic]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # 清理资源
            del self.active_streams[topic]
            if topic in self.stream_configs:
                del self.stream_configs[topic]
            if topic in self.last_data:
                del self.last_data[topic]
            if topic in self.stream_stats:
                del self.stream_stats[topic]

            logger.info(f"停止数据流: {topic}")
            return True

        except Exception as e:
            logger.error(f"停止数据流 {topic} 失败: {e}")
            return False

    async def _data_stream_worker(self, topic: str, topic_info: dict[str, Any]) -> None:
        """
        数据流工作器

        Args:
            topic: 数据流主题
            topic_info: 主题信息
        """
        try:
            data_type = topic_info["type"]
            symbol = topic_info["symbol"]
            interval = topic_info["interval"]

            # 根据间隔确定更新频率
            update_interval = self._get_update_interval(interval)

            logger.info(f"数据流工作器启动: {topic}, 更新间隔: {update_interval}秒")

            while True:
                try:
                    # 检查是否还有订阅者
                    subscribers = self.connection_manager.get_topic_subscribers(topic)
                    if not subscribers:
                        logger.debug(f"主题 {topic} 没有订阅者，暂停数据流")
                        await asyncio.sleep(update_interval)
                        continue

                    # 获取数据
                    data = await self._fetch_real_time_data(data_type, symbol, interval)

                    if data:
                        # 检查数据是否有更新
                        if self._is_data_updated(topic, data):
                            # 推送数据
                            await self._push_data(topic, data)

                            # 更新统计
                            if topic in self.stream_stats:
                                self.stream_stats[topic]["messages_sent"] += 1
                                self.stream_stats[topic]["last_update"] = (
                                    datetime.utcnow()
                                )

                    # 等待下次更新
                    await asyncio.sleep(update_interval)

                except Exception as e:
                    logger.error(f"数据流 {topic} 处理出错: {e}")

                    # 更新错误统计
                    if topic in self.stream_stats:
                        self.stream_stats[topic]["errors"] += 1

                    # 短暂等待后重试
                    await asyncio.sleep(min(update_interval, 10))

        except asyncio.CancelledError:
            logger.debug(f"数据流工作器 {topic} 被取消")
        except Exception as e:
            logger.error(f"数据流工作器 {topic} 异常退出: {e}")

    async def _fetch_real_time_data(
        self, data_type: str, symbol: str, interval: str
    ) -> dict[str, Any] | None:
        """
        获取实时数据

        Args:
            data_type: 数据类型
            symbol: 交易符号
            interval: 时间间隔

        Returns:
            Optional[Dict]: 实时数据
        """
        try:
            if data_type == "stock":
                return await self._fetch_stock_data(symbol, interval)
            elif data_type == "crypto":
                return await self._fetch_crypto_data(symbol, interval)
            elif data_type == "futures":
                return await self._fetch_futures_data(symbol, interval)
            elif data_type == "market":
                return await self._fetch_market_summary(symbol)
            else:
                logger.warning(f"不支持的数据类型: {data_type}")
                return None

        except Exception as e:
            logger.error(f"获取实时数据失败 {data_type}.{symbol}.{interval}: {e}")
            return None

    async def _fetch_stock_data(
        self, symbol: str, interval: str
    ) -> dict[str, Any] | None:
        """
        获取股票实时数据

        Args:
            symbol: 股票代码
            interval: 时间间隔

        Returns:
            Optional[Dict]: 股票数据
        """
        try:
            # 首先尝试从缓存获取
            cache_key = f"realtime:stock:{symbol}:{interval}"
            cached_data = await self.redis_manager.get(cache_key)

            if cached_data:
                return json.loads(cached_data)

            # 从数据获取器获取最新数据
            # 需要确定市场类型，这里简化处理，可以根据symbol前缀判断
            market_type = "A_share" if symbol.endswith((".SH", ".SZ")) else "US_stock"
            data = await fetch_stock_data(symbol, interval, market_type)

            if data and len(data) > 0:
                latest_data = data[-1]  # 获取最新的数据点

                # 格式化数据
                formatted_data = {
                    "symbol": symbol,
                    "price": latest_data.get("close"),
                    "open": latest_data.get("open"),
                    "high": latest_data.get("high"),
                    "low": latest_data.get("low"),
                    "volume": latest_data.get("volume"),
                    "change": latest_data.get("change"),
                    "change_percent": latest_data.get("change_percent"),
                    "timestamp": latest_data.get(
                        "timestamp", datetime.utcnow().isoformat()
                    ),
                }

                # 缓存数据（短时间缓存）
                await self.redis_manager.set(
                    cache_key,
                    json.dumps(formatted_data, ensure_ascii=False),
                    ex=30,  # 30秒缓存
                )

                return formatted_data

            return None

        except Exception as e:
            logger.error(f"获取股票数据失败 {symbol}: {e}")
            return None

    async def _fetch_crypto_data(
        self, symbol: str, interval: str
    ) -> dict[str, Any] | None:
        """
        获取加密货币实时数据

        Args:
            symbol: 加密货币代码
            interval: 时间间隔

        Returns:
            Optional[Dict]: 加密货币数据
        """
        try:
            # 这里可以集成加密货币数据源
            # 暂时返回模拟数据
            return {
                "symbol": symbol,
                "price": 50000.0,
                "volume": 1000000,
                "change_percent": 2.5,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"获取加密货币数据失败 {symbol}: {e}")
            return None

    async def _fetch_futures_data(
        self, symbol: str, interval: str
    ) -> dict[str, Any] | None:
        """
        获取期货实时数据

        Args:
            symbol: 期货代码
            interval: 时间间隔

        Returns:
            Optional[Dict]: 期货数据
        """
        try:
            # 这里可以集成期货数据源
            # 暂时返回模拟数据
            return {
                "symbol": symbol,
                "price": 4500.0,
                "volume": 50000,
                "change_percent": -1.2,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"获取期货数据失败 {symbol}: {e}")
            return None

    async def _fetch_market_summary(self, market: str) -> dict[str, Any] | None:
        """
        获取市场概览数据

        Args:
            market: 市场代码

        Returns:
            Optional[Dict]: 市场概览数据
        """
        try:
            # 这里可以集成市场概览数据源
            # 暂时返回模拟数据
            return {
                "market": market,
                "index_value": 4500.0,
                "change": 50.0,
                "change_percent": 1.1,
                "volume": 1000000000,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"获取市场概览失败 {market}: {e}")
            return None

    def _parse_topic(self, topic: str) -> dict[str, Any] | None:
        """
        解析主题

        Args:
            topic: 主题字符串

        Returns:
            Optional[Dict]: 解析后的主题信息
        """
        try:
            parts = topic.split(".")

            if len(parts) < 2:
                return None

            if parts[0] == "market" and len(parts) == 3:
                return {"type": "market", "symbol": parts[1], "interval": "summary"}
            elif len(parts) == 3:
                return {"type": parts[0], "symbol": parts[1], "interval": parts[2]}

            return None

        except Exception:
            return None

    def _get_update_interval(self, interval: str) -> int:
        """
        根据数据间隔获取更新频率

        Args:
            interval: 数据间隔

        Returns:
            int: 更新间隔（秒）
        """
        interval_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "summary": 300,  # 市场概览5分钟更新一次
        }

        return interval_map.get(interval, 300)  # 默认5分钟

    def _is_data_updated(self, topic: str, new_data: dict[str, Any]) -> bool:
        """
        检查数据是否有更新

        Args:
            topic: 主题
            new_data: 新数据

        Returns:
            bool: 数据是否有更新
        """
        try:
            if topic not in self.last_data:
                self.last_data[topic] = new_data
                return True

            last_data = self.last_data[topic]

            # 比较关键字段
            key_fields = ["price", "volume", "timestamp"]

            for field in key_fields:
                if new_data.get(field) != last_data.get(field):
                    self.last_data[topic] = new_data
                    return True

            return False

        except Exception as e:
            logger.error(f"检查数据更新失败: {e}")
            return True  # 出错时默认认为有更新

    async def _push_data(self, topic: str, data: dict[str, Any]) -> None:
        """
        推送数据到订阅者

        Args:
            topic: 主题
            data: 要推送的数据
        """
        try:
            message = {"type": "data", "data": data}

            sent_count = await self.connection_manager.broadcast_to_topic(
                topic, message
            )

            if sent_count > 0:
                logger.debug(f"推送数据到主题 {topic}，接收者: {sent_count}")

        except Exception as e:
            logger.error(f"推送数据失败 {topic}: {e}")

    async def _cleanup_inactive_streams(self) -> None:
        """
        清理不活跃的数据流
        """
        try:
            while True:
                await asyncio.sleep(300)  # 每5分钟检查一次

                inactive_topics = []

                for topic in list(self.active_streams.keys()):
                    # 检查是否还有订阅者
                    subscribers = self.connection_manager.get_topic_subscribers(topic)

                    if not subscribers:
                        # 检查是否已经没有订阅者超过5分钟
                        if topic in self.stream_stats:
                            last_update = self.stream_stats[topic].get("last_update")
                            if last_update:
                                time_diff = (
                                    datetime.utcnow() - last_update
                                ).total_seconds()
                                if time_diff > 300:  # 5分钟
                                    inactive_topics.append(topic)
                            else:
                                # 如果从未更新过，也认为是不活跃的
                                started_at = self.stream_stats[topic].get("started_at")
                                if started_at:
                                    time_diff = (
                                        datetime.utcnow() - started_at
                                    ).total_seconds()
                                    if time_diff > 300:
                                        inactive_topics.append(topic)

                # 停止不活跃的数据流
                for topic in inactive_topics:
                    await self.stop_data_stream(topic)
                    logger.info(f"清理不活跃的数据流: {topic}")

        except asyncio.CancelledError:
            logger.debug("数据流清理任务被取消")
        except Exception as e:
            logger.error(f"清理不活跃数据流时出错: {e}")

    def get_stream_stats(self) -> dict[str, Any]:
        """
        获取数据流统计信息

        Returns:
            Dict: 数据流统计信息
        """
        return {
            "active_streams": len(self.active_streams),
            "stream_details": self.stream_stats.copy(),
        }

    async def shutdown(self) -> None:
        """
        关闭数据流服务
        """
        try:
            # 取消清理任务
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass

            # 停止所有数据流
            topics = list(self.active_streams.keys())
            for topic in topics:
                await self.stop_data_stream(topic)

            logger.info("数据流服务已关闭")

        except Exception as e:
            logger.error(f"关闭数据流服务时出错: {e}")

    async def handle_subscription_change(self, topic: str, action: str) -> None:
        """
        处理订阅变化

        Args:
            topic: 主题
            action: 动作 (subscribe/unsubscribe)
        """
        try:
            if action == "subscribe":
                # 有新订阅者，启动数据流
                if topic not in self.active_streams:
                    await self.start_data_stream(topic)
            elif action == "unsubscribe":
                # 检查是否还有其他订阅者
                subscribers = self.connection_manager.get_topic_subscribers(topic)
                if not subscribers and topic in self.active_streams:
                    # 延迟停止，给其他可能的订阅者一些时间
                    await asyncio.sleep(30)
                    subscribers = self.connection_manager.get_topic_subscribers(topic)
                    if not subscribers:
                        await self.stop_data_stream(topic)

        except Exception as e:
            logger.error(f"处理订阅变化失败 {topic}: {e}")
