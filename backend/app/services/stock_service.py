#!/usr/bin/env python3
"""
股票数据服务层
集成多级缓存的股票数据查询和管理服务
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from app.data.managers import data_manager
from app.infrastructure.cache import cache_service, smart_cache
from app.schemas.stock import StockDataBase, StockInfo

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.infrastructure.database import models

logger = logging.getLogger(__name__)


class CachedStockService:
    """带缓存的股票数据服务

    提供股票数据的查询、缓存和管理功能
    """

    def __init__(self):
        """初始化股票服务"""
        self.cache = cache_service

        # 缓存配置
        self.cache_config = {
            "stock_list": {
                "ttl": 86400,  # 24小时
                "use_multi_level": True,
            },
            "stock_data": {
                "ttl": 3600,  # 1小时
                "use_multi_level": False,  # 数据量大，仅使用Redis
            },
            "fundamental_data": {
                "ttl": 86400,  # 24小时
                "use_multi_level": True,
            },
            "corporate_actions": {
                "ttl": 86400,  # 24小时
                "use_multi_level": True,
            },
            "annual_earnings": {
                "ttl": 86400,  # 24小时
                "use_multi_level": True,
            },
        }

    @smart_cache("stock_info", lambda self, market_type: f"list_{market_type}")
    async def get_stock_list(
        self, db: Session, market_type: str = "A_share"
    ) -> list[StockInfo]:
        """获取股票列表（带缓存）

        Args:
            db: 数据库会话
            market_type: 市场类型

        Returns:
            股票信息列表
        """
        try:
            logger.info(f"Fetching stock list for market: {market_type}")

            # 从数据库获取股票列表
            stocks = data_manager.get_all_stocks_list(db, market_type)

            # 转换为Pydantic模型
            stock_list = []
            for stock in stocks:
                stock_info = StockInfo(ts_code=stock.ts_code, name=stock.name)
                stock_list.append(stock_info)

            logger.info(f"Retrieved {len(stock_list)} stocks for {market_type}")
            return stock_list

        except Exception as e:
            logger.exception(f"Error fetching stock list for {market_type}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch stock list: {e!s}"
            ) from e

    async def refresh_stock_list(
        self, db: Session, market_type: str = "A_share"
    ) -> dict[str, Any]:
        """刷新股票列表并清除缓存

        Args:
            db: 数据库会话
            market_type: 市场类型

        Returns:
            刷新结果
        """
        try:
            logger.info(f"Force refreshing stock list for market: {market_type}")

            # 强制更新股票列表
            data_manager.force_update_stock_list(db, market_type)

            # 清除相关缓存
            cache_key = self.cache.key_manager.generate_key(
                "stock_info", f"list_{market_type}"
            )
            self.cache.redis_cache.delete(cache_key)

            # 预热缓存
            await self.get_stock_list(db, market_type)

            return {
                "message": f"Stock list for {market_type} refreshed successfully",
                "market_type": market_type,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error refreshing stock list for {market_type}")
            raise HTTPException(
                status_code=500, detail=f"Failed to refresh stock list: {e!s}"
            ) from e

    async def get_stock_data(
        self,
        stock_code: str,
        interval: str = "daily",
        market_type: str = "A_share",
        trade_date: date | None = None,
    ) -> list[StockDataBase]:
        """获取股票数据（带缓存）

        Args:
            stock_code: 股票代码
            interval: 时间间隔
            market_type: 市场类型
            trade_date: 交易日期

        Returns:
            股票数据列表
        """
        try:
            # 生成缓存键
            cache_params = {
                "stock_code": stock_code,
                "interval": interval,
                "market_type": market_type,
                "trade_date": trade_date.isoformat() if trade_date else None,
            }
            cache_key_suffix = hashlib.sha256(str(cache_params).encode()).hexdigest()

            # 对于分钟级和5日线数据，不使用缓存（数据变化频繁）
            if interval in ["minute", "5day"]:
                return await self._fetch_stock_data_direct(
                    stock_code, interval, market_type, trade_date
                )

            # 尝试从缓存获取
            cached_data = await self.cache.get_stock_daily_data(
                stock_code, cache_key_suffix, market_type
            )
            if cached_data is not None:
                logger.debug(f"Cache hit for stock data: {stock_code}")
                return cached_data

            # 缓存未命中，从数据源获取
            logger.debug(f"Cache miss for stock data: {stock_code}")
            stock_data = await self._fetch_stock_data_direct(
                stock_code, interval, market_type, trade_date
            )

            # 缓存结果（仅对日线及以上级别数据缓存）
            if interval in ["daily", "weekly", "monthly"] and stock_data:
                await self.cache.set_stock_daily_data(
                    stock_code, cache_key_suffix, stock_data, market_type
                )

            return stock_data

        except Exception as e:
            logger.exception(f"Error fetching stock data for {stock_code}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch stock data: {e!s}"
            ) from e

    async def _fetch_stock_data_direct(
        self,
        stock_code: str,
        interval: str,
        market_type: str,
        trade_date: date | None,
    ) -> list[StockDataBase]:
        """直接从数据源获取股票数据

        Args:
            stock_code: 股票代码
            interval: 时间间隔
            market_type: 市场类型
            trade_date: 交易日期

        Returns:
            股票数据列表
        """
        # 验证A股代码格式
        if market_type == "A_share" and "." not in stock_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid A-share stock_code format. Expected format: '<code>.<market>' (e.g., '600519.SH')",
            )

        # 使用现有的数据获取逻辑
        df = data_manager.fetch_stock_data(
            stock_code=stock_code,
            interval=interval,
            market_type=market_type,
            trade_date=trade_date,
        )

        if df.empty:
            return []

        # 转换为Pydantic模型
        dict_records = df.to_dict(orient="records")
        for record in dict_records:
            record["ts_code"] = stock_code
            record["interval"] = interval

        records = [StockDataBase.model_validate(record) for record in dict_records]
        return records

    @smart_cache("stock_info", lambda self, symbol: f"fundamental_{symbol}")
    async def get_fundamental_data(self, db: Session, symbol: str) -> Any | None:
        """获取基本面数据（带缓存）

        Args:
            db: 数据库会话
            symbol: 股票代码

        Returns:
            基本面数据
        """
        try:
            logger.debug(f"Fetching fundamental data for: {symbol}")

            # 解析股票代码
            resolved_symbol = data_manager.resolve_symbol(db, symbol)
            if not resolved_symbol:
                raise HTTPException(
                    status_code=404, detail=f"Symbol '{symbol}' not found."
                )

            # 从数据库获取基本面数据
            fundamental_data = data_manager.get_fundamental_data_from_db(
                db, resolved_symbol
            )

            return fundamental_data

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error fetching fundamental data for {symbol}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch fundamental data: {e!s}"
            ) from e

    @smart_cache("stock_info", lambda self, symbol: f"corporate_actions_{symbol}")
    async def get_corporate_actions(
        self, db: Session, symbol: str
    ) -> list[models.CorporateAction]:
        """获取公司行动数据（带缓存）

        Args:
            db: 数据库会话
            symbol: 股票代码

        Returns:
            公司行动数据列表
        """
        try:
            logger.debug(f"Fetching corporate actions for: {symbol}")

            # 解析股票代码
            resolved_symbol = data_manager.resolve_symbol(db, symbol)
            if not resolved_symbol:
                raise HTTPException(
                    status_code=404, detail=f"Symbol '{symbol}' not found."
                )

            # 从数据库获取公司行动数据
            actions = data_manager.get_corporate_actions_from_db(db, resolved_symbol)

            return actions

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error fetching corporate actions for {symbol}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch corporate actions: {e!s}"
            ) from e

    @smart_cache("stock_info", lambda self, symbol: f"annual_earnings_{symbol}")
    async def get_annual_earnings(
        self, db: Session, symbol: str
    ) -> list[models.AnnualEarnings]:
        """获取年度收益数据（带缓存）

        Args:
            db: 数据库会话
            symbol: 股票代码

        Returns:
            年度收益数据列表
        """
        try:
            logger.debug(f"Fetching annual earnings for: {symbol}")

            # 解析股票代码
            resolved_symbol = data_manager.resolve_symbol(db, symbol)
            if not resolved_symbol:
                raise HTTPException(
                    status_code=404, detail=f"Symbol '{symbol}' not found."
                )

            # 从数据库获取年度收益数据
            earnings = data_manager.get_annual_earnings_from_db(db, resolved_symbol)

            return earnings

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error fetching annual earnings for {symbol}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch annual earnings: {e!s}"
            ) from e

    async def invalidate_stock_cache(
        self, stock_code: str, market_type: str = "A_share"
    ):
        """失效股票相关缓存

        Args:
            stock_code: 股票代码
            market_type: 市场类型
        """
        try:
            logger.info(f"Invalidating cache for stock: {stock_code}")

            # 失效股票数据缓存
            self.cache.invalidate_stock_data(stock_code, market_type)

            # 失效相关的基本面数据缓存
            patterns = [
                f"stock_info:fundamental_{stock_code}*",
                f"stock_info:corporate_actions_{stock_code}*",
                f"stock_info:annual_earnings_{stock_code}*",
            ]

            for pattern in patterns:
                deleted_count = self.cache.redis_cache.delete_pattern(pattern)
                logger.debug(
                    f"Deleted {deleted_count} cache entries for pattern: {pattern}"
                )

            logger.info(f"Cache invalidation completed for stock: {stock_code}")

        except Exception:
            logger.exception(f"Error invalidating cache for {stock_code}")

    async def preload_hot_stocks(
        self, db: Session, market_type: str = "A_share", limit: int = 100
    ):
        """预加载热门股票数据

        Args:
            db: 数据库会话
            market_type: 市场类型
            limit: 预加载股票数量限制
        """
        try:
            logger.info(f"Starting preload for hot stocks in {market_type}")

            # 获取热门股票列表（这里简化为获取前N只股票）
            stocks = data_manager.get_all_stocks_list(db, market_type)
            hot_stocks = stocks[:limit]

            preload_count = 0
            for stock in hot_stocks:
                try:
                    # 预加载股票基本信息
                    await self.get_stock_list(db, market_type)

                    # 预加载最近的日线数据
                    await self.get_stock_data(stock.ts_code, "daily", market_type)

                    preload_count += 1

                    if preload_count % 10 == 0:
                        logger.info(
                            f"Preloaded {preload_count}/{len(hot_stocks)} stocks"
                        )

                except Exception as e:
                    logger.warning(f"Failed to preload data for {stock.ts_code}: {e}")
                    continue

            logger.info(f"Preload completed: {preload_count}/{len(hot_stocks)} stocks")

        except Exception:
            logger.exception("Error during hot stocks preload")

    async def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            缓存统计信息
        """
        try:
            stats = self.cache.get_comprehensive_stats()

            # 添加服务层特定的统计信息
            service_stats = {
                "service_name": "CachedStockService",
                "cache_config": self.cache_config,
                "timestamp": datetime.now().isoformat(),
            }

            return {"service_stats": service_stats, "cache_stats": stats}

        except Exception as e:
            logger.exception("Error getting cache stats")
            return {"error": str(e)}

    async def health_check(self) -> dict[str, Any]:
        """服务健康检查

        Returns:
            健康检查结果
        """
        try:
            # 检查缓存健康状态
            cache_health = await self.cache.health_check()

            # 获取详细的缓存健康检查信息
            detailed_cache_health = self.cache.get_detailed_health_check()

            # 如果基本健康检查失败，更新详细状态
            if not cache_health:
                detailed_cache_health["overall_status"] = "unhealthy"

            # 检查服务状态
            service_health = {
                "service_name": "CachedStockService",
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
            }

            # 综合健康状态
            overall_status = "healthy"
            if detailed_cache_health["overall_status"] != "healthy":
                overall_status = "degraded"

            return {
                "overall_status": overall_status,
                "service_health": service_health,
                "cache_health": detailed_cache_health,
            }

        except Exception as e:
            logger.exception("Error during health check")
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# 全局股票服务实例
stock_service = CachedStockService()
