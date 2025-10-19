from __future__ import annotations

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """通用消息响应模型，用于非数据返回的提示信息（例如 202 Accepted）。"""

    message: str
