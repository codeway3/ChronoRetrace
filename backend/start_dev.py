#!/usr/bin/env python3
"""
Development server startup script for ChronoRetrace backend.
This script configures uvicorn to only watch the backend directory for changes,
avoiding issues with frontend node_modules directory.
"""

import logging
from pathlib import Path
from typing import ClassVar

import uvicorn


class ColoredFormatter(logging.Formatter):
    """自定义彩色日志格式化器"""

    # ANSI颜色代码
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[41m",  # 红色背景
        "RESET": "\033[0m",  # 重置
    }

    def format(self, record):
        # 获取颜色
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # 格式化消息
        formatted = super().format(record)
        return f"{color}{formatted}{reset}"


if __name__ == "__main__":
    # Configure colorful logging with timestamp
    handler = logging.StreamHandler()
    handler.setFormatter(
        ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # 清除现有的处理器
    logger.handlers.clear()
    logger.addHandler(handler)

    # Get the backend directory path
    backend_dir = Path(__file__).parent.absolute()

    # Configure uvicorn to only reload based on changes in the backend directory
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir)],  # Only watch the backend directory
        log_level="info",
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "colored": {
                    "()": "__main__.ColoredFormatter",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "access": {
                    "()": "__main__.ColoredFormatter",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "colored",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO"},
                "uvicorn.error": {"level": "INFO"},
                "uvicorn.access": {
                    "handlers": ["access"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        },
    )
