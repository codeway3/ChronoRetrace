"""
WebSocket API路由

提供WebSocket连接端点和相关管理接口
"""

import contextlib
import json
import logging
from datetime import datetime

from fastapi import (
    APIRouter,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.security import HTTPBearer

from app.core.config import settings
from app.infrastructure.cache.redis_manager import RedisCacheManager
from app.services.auth_service import auth_service
from app.websocket.connection_manager import ConnectionManager
from app.websocket.data_stream_service import DataStreamService
from app.websocket.message_handler import MessageHandler

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 安全认证
security = HTTPBearer()

# 全局实例（将在应用启动时初始化）
connection_manager: ConnectionManager | None = None
message_handler: MessageHandler | None = None
# 恢复全局 data_stream_service 变量定义，同时保留对局部未使用变量赋值的移除。
data_stream_service: DataStreamService | None = None


def init_websocket_services(app: FastAPI, redis_manager: RedisCacheManager):
    """
    初始化WebSocket服务

    Args:
        app: FastAPI应用实例，用于在 app.state 中注册服务对象
        redis_manager: Redis缓存管理器实例
    """
    # 使用应用状态存储服务实例，避免使用全局变量
    # 依赖 main.py 中已创建的 connection_manager 与 data_stream_service
    connection_manager = getattr(app.state, "connection_manager", None)
    if connection_manager is None:
        # 若未预先创建，则按需创建一个（保证函数健壮）
        connection_manager = ConnectionManager(
            heartbeat_interval_seconds=settings.WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS
        )
        app.state.connection_manager = connection_manager

    # 初始化并注册消息处理器
    app.state.message_handler = MessageHandler(connection_manager)

    # 保存 redis_manager 到应用状态，确保参数被使用且可供后续服务访问
    app.state.redis_manager = redis_manager

    logger.info("WebSocket services initialized successfully")


async def get_current_user_from_token(token: str) -> dict | None:
    """
    从token获取当前用户信息

    Args:
        token: JWT token

    Returns:
        Optional[dict]: 用户信息
    """
    try:
        payload = auth_service.verify_token(token)
        if payload:
            return {"user_id": payload.get("sub"), "username": payload.get("username")}
        else:
            return None
    except Exception:
        logger.exception("解析token失败")
        return None


@router.websocket("/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, client_id: str, token: str | None = None
):
    """
    WebSocket连接端点

    Args:
        websocket: WebSocket连接对象
        client_id: 客户端唯一标识
        token: 可选的认证token（通过查询参数传递）
    """
    logger.info(
        f"WebSocket连接请求: client_id={client_id}, token={'***' if token else 'None'}"
    )

    # 从app.state获取服务实例
    app = websocket.app
    connection_manager = getattr(app.state, "connection_manager", None)
    # 移除未使用的局部变量赋值，避免遮蔽全局 data_stream_service 并产生未使用警告

    if not connection_manager:
        logger.error("WebSocket服务未初始化 - connection_manager为空")
        try:
            await websocket.close(code=1011, reason="WebSocket服务未初始化")
        except Exception:
            logger.exception("关闭WebSocket连接时出错")
        return

    # 创建消息处理器
    try:
        message_handler = MessageHandler(connection_manager)
    except Exception:
        logger.exception("创建消息处理器失败")
        with contextlib.suppress(Exception):
            await websocket.close(code=1011, reason="消息处理器初始化失败")
        return

    user_info = None

    # 如果提供了token，验证用户身份
    if token:
        user_info = await get_current_user_from_token(token)
        if not user_info:
            logger.warning(f"客户端 {client_id} 提供了无效的认证token")
            try:
                await websocket.close(code=1008, reason="无效的认证token")
            except Exception:
                logger.exception("关闭WebSocket连接时出错")
            return

    # 建立连接
    try:
        success = await connection_manager.connect(
            websocket, client_id, user_info.get("user_id") if user_info else None
        )

        if not success:
            logger.error(f"客户端 {client_id} 连接建立失败")
            try:
                await websocket.close(code=1011, reason="连接建立失败")
            except Exception:
                logger.exception("关闭WebSocket连接时出错")
            return

    except Exception:
        logger.exception("建立WebSocket连接时出错")
        with contextlib.suppress(Exception):
            await websocket.close(code=1011, reason="连接建立异常")
        return

    try:
        # 消息处理循环
        while True:
            try:
                # 检查连接状态
                if websocket.client_state.name != "CONNECTED":
                    logger.warning(
                        f"客户端 {client_id} WebSocket状态异常: {websocket.client_state.name}"
                    )
                    break

                # 接收客户端消息
                message = await websocket.receive_text()

                # 验证消息格式
                try:
                    json.loads(message)  # 验证JSON格式
                except json.JSONDecodeError as json_error:
                    logger.warning(
                        f"客户端 {client_id} 发送了无效的JSON消息: {json_error}"
                    )
                    await connection_manager.send_to_client(
                        client_id,
                        {
                            "type": "error",
                            "error_code": "invalid_json",
                            "error_message": "消息格式错误, 请发送有效的JSON",
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                    continue

                # 处理消息
                await message_handler.handle_message(client_id, message)

            except WebSocketDisconnect:
                logger.info(f"客户端 {client_id} 主动断开连接")
                break
            except ConnectionResetError:
                logger.info(f"客户端 {client_id} 连接被重置")
                break
            except Exception as e:
                error_msg = str(e).lower()
                logger.exception(f"处理客户端 {client_id} 消息时出错")

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
                    logger.info(f"检测到客户端 {client_id} 连接问题, 断开连接")
                    break

                # 发送错误消息给客户端
                try:
                    await connection_manager.send_to_client(
                        client_id,
                        {
                            "type": "error",
                            "error_code": "message_processing_error",
                            "error_message": "消息处理错误",
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                except Exception:
                    logger.exception("向客户端 %s 发送错误消息失败", client_id)
                    break  # 如果无法发送错误消息，断开连接

    except Exception:
        logger.exception("WebSocket连接 %s 异常", client_id)
    finally:
        # 清理连接
        try:
            await connection_manager.disconnect(client_id)
            logger.debug(f"客户端 {client_id} 连接清理完成")
        except Exception:
            logger.exception("清理客户端 %s 连接时出错", client_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    获取WebSocket连接统计信息

    Returns:
        dict: 连接统计信息
    """
    if not connection_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket服务未初始化",
        )

    connection_stats = connection_manager.get_connection_stats()

    stream_stats = {}
    if data_stream_service:
        stream_stats = data_stream_service.get_stream_stats()

    return {
        "connections": connection_stats,
        "streams": stream_stats,
        "message_types": (
            message_handler.get_supported_message_types() if message_handler else []
        ),
        "topic_examples": (
            message_handler.get_topic_examples() if message_handler else {}
        ),
    }


@router.get("/ws/activity")
async def get_websocket_activity():
    """
    获取WebSocket活动简要指标，仅返回计数，不包含敏感信息。

    Returns:
        dict: 活动计数信息
    """
    if not connection_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket服务未初始化",
        )

    stats = connection_manager.get_connection_stats()
    return {
        "total_connections": stats.get("total_connections", 0),
        "total_subscriptions": stats.get("total_subscriptions", 0),
        "topics_count": stats.get("topics_count", 0),
    }


@router.get("/ws/connections")
async def get_active_connections():
    """
    获取活跃连接列表

    Returns:
        dict: 活跃连接信息
    """
    if not connection_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket服务未初始化",
        )

    stats = connection_manager.get_connection_stats()

    return {
        "total_connections": stats["total_connections"],
        "connections": [
            {
                "client_id": client_id,
                "subscriptions": info["subscriptions"],
                "connected_at": info["metadata"].get("connected_at"),
                "user_id": info["metadata"].get("user_id"),
            }
            for client_id, info in stats["connections"].items()
        ],
    }


@router.get("/ws/topics")
async def get_active_topics(request: Request):
    """
    获取活跃主题列表

    Returns:
        dict: 活跃主题信息
    """
    cm = getattr(request.app.state, "connection_manager", None)
    if cm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket服务未初始化",
        )

    stats = cm.get_connection_stats()

    # 统计每个主题的订阅者数量
    topic_stats = {}
    for client_id, info in stats["connections"].items():
        for topic in info["subscriptions"]:
            if topic not in topic_stats:
                topic_stats[topic] = {
                    "topic": topic,
                    "subscribers": 0,
                    "subscriber_ids": [],
                }
            topic_stats[topic]["subscribers"] += 1
            topic_stats[topic]["subscriber_ids"].append(client_id)

    return {"total_topics": len(topic_stats), "topics": list(topic_stats.values())}


@router.post("/ws/broadcast/{topic}")
async def broadcast_message(request: Request, topic: str, message: dict):
    """
    向指定主题广播消息（管理员功能）

    Args:
        topic: 主题名称
        message: 要广播的消息

    Returns:
        dict: 广播结果
    """
    cm = getattr(request.app.state, "connection_manager", None)
    if cm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket服务未初始化",
        )

    try:
        sent_count = await cm.broadcast_to_topic(topic, message)
    except Exception as e:
        logger.exception("广播消息失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="广播消息失败",
        ) from e
    else:
        return {
            "success": True,
            "topic": topic,
            "sent_count": sent_count,
            "message": "消息广播成功",
        }


@router.delete("/ws/connections/{client_id}")
async def disconnect_client(request: Request, client_id: str):
    """
    断开指定客户端连接（管理员功能）

    Args:
        client_id: 客户端ID

    Returns:
        dict: 断开结果
    """
    cm = getattr(request.app.state, "connection_manager", None)
    if cm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket服务未初始化",
        )

    try:
        await cm.disconnect(client_id)
    except Exception as e:
        logger.exception("断开客户端连接失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="断开连接失败",
        ) from e
    else:
        return {"success": True, "client_id": client_id, "message": "客户端连接已断开"}


@router.post("/ws/cleanup")
async def cleanup_inactive_connections(request: Request):
    """
    清理不活跃的连接（管理员功能）

    Returns:
        dict: 清理结果
    """
    cm = getattr(request.app.state, "connection_manager", None)
    if cm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket服务未初始化",
        )

    try:
        cleaned_count = await cm.cleanup_inactive_connections()
    except Exception as e:
        logger.exception("清理不活跃连接失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清理失败",
        ) from e
    else:
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"清理了 {cleaned_count} 个不活跃的连接",
        }


# 获取WebSocket服务实例的辅助函数
def get_connection_manager(app: FastAPI) -> ConnectionManager:
    """
    获取连接管理器实例

    Returns:
        ConnectionManager: 连接管理器实例
    """

    cm = getattr(app.state, "connection_manager", None)
    if cm is None:
        raise HTTPException(status_code=500, detail="WebSocket服务未初始化")
    return cm


def get_data_stream_service(app: FastAPI) -> DataStreamService:
    """获取数据流服务实例"""
    dss = getattr(app.state, "data_stream_service", None)
    if dss is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据流服务未初始化",
        )
    return dss


async def shutdown_websocket_services(app: FastAPI):
    """
    关闭WebSocket服务
    """

    try:
        dss = getattr(app.state, "data_stream_service", None)
        if dss:
            await dss.shutdown()

        cm = getattr(app.state, "connection_manager", None)
        if cm:
            # 断开所有连接
            stats = cm.get_connection_stats()
            for client_id in list(stats["connections"].keys()):
                await cm.disconnect(client_id)

        logger.info("WebSocket服务已关闭")

    except Exception:
        logger.exception("关闭WebSocket服务时出错")
    finally:
        app.state.connection_manager = None
        app.state.message_handler = None
        app.state.data_stream_service = None
