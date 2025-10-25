"""

ChronoRetrace - 缓存预热服务

本模块提供缓存预热和增量更新功能，确保热点数据始终在缓存中可用，
提升系统响应速度和用户体验。

Author: ChronoRetrace Team
Date: 2024
"""

from __future__ import annotations

import inspect

# !/usr/bin/env python3
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.infrastructure.database.models import DailyStockMetrics, StockData, StockInfo
from app.infrastructure.database.session import SessionLocal

from .cache_service import cache_service
from .redis_manager import CacheKeyManager

logger = logging.getLogger(__name__)


class CacheWarmingService:
    """
    缓存预热服务

    负责预热热点数据、增量更新缓存、监控缓存状态等功能。
    """

    def __init__(self):
        """
        初始化缓存预热服务
        """
        self.key_manager = CacheKeyManager()
        self.cache_service = cache_service
        self.warming_stats = {
            "last_warming_time": None,
            "total_keys_warmed": 0,
            "warming_duration_seconds": 0,
            "failed_keys": 0,
        }
        self.hot_stocks: set[str] = set()
        self.warming_in_progress = False

    async def warm_all_caches(self, force: bool = False) -> dict[str, Any]:
        """
        预热所有缓存

        Args:
            force: 是否强制预热（忽略现有缓存）

        Returns:
            Dict[str, Any]: 预热结果统计
        """
        if self.warming_in_progress and not force:
            logger.warning("缓存预热正在进行中，跳过此次请求")
            return {"status": "skipped", "reason": "warming_in_progress"}

        self.warming_in_progress = True
        start_time = datetime.now()

        try:
            logger.info("开始缓存预热...")

            # 预热统计
            stats = {
                "stock_list": 0,
                "hot_stocks_data": 0,
                "market_metrics": 0,
                "fundamental_data": 0,
                "failed": 0,
            }

            # 1. 预热股票列表
            await self._warm_stock_lists(stats, force)

            # 2. 预热热点股票数据
            await self._warm_hot_stocks_data(stats, force)

            # 3. 预热市场指标
            await self._warm_market_metrics(stats, force)

            # 4. 预热基本面数据
            await self._warm_fundamental_data(stats, force)

            # 更新统计信息
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.warming_stats.update(
                {
                    "last_warming_time": end_time,
                    "total_keys_warmed": sum(
                        v for k, v in stats.items() if k != "failed"
                    ),
                    "warming_duration_seconds": duration,
                    "failed_keys": stats["failed"],
                }
            )

            logger.info(
                f"缓存预热完成，耗时 {duration:.2f} 秒，预热 {self.warming_stats['total_keys_warmed']} 个键"
            )

            return {
                "status": "completed",
                "duration_seconds": duration,
                "stats": stats,
                "timestamp": end_time.isoformat(),
            }

        except Exception as e:
            logger.error(f"缓存预热失败: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            self.warming_in_progress = False

    async def _warm_stock_lists(self, stats: dict[str, int], force: bool = False):
        """
        预热股票列表缓存

        Args:
            stats: 统计信息字典
            force: 是否强制预热
        """
        try:
            db = SessionLocal()
            try:
                # 预热A股列表
                # 检查A股列表缓存
                a_share_stock_code = "list_A_share"
                cached_data = await cache_service.get_stock_info(
                    a_share_stock_code, "A_share"
                )
                logger.debug(
                    f"A股缓存检查结果: {cached_data is not None}, force={force}"
                )

                if force or not cached_data:
                    a_shares = (
                        db.query(StockInfo)
                        .filter(
                            StockInfo.ts_code.like("%.SZ")
                            | StockInfo.ts_code.like("%.SH")
                        )
                        .all()
                    )
                    logger.debug(f"从数据库查询到 {len(a_shares)} 只A股")

                    a_share_data = [
                        {
                            "ts_code": stock.ts_code,
                            "name": stock.name,
                            "market_type": stock.market_type,
                        }
                        for stock in a_shares
                    ]

                    success = await cache_service.set_stock_info(
                        a_share_stock_code, a_share_data, "A_share"
                    )
                    logger.debug(f"A股缓存设置结果: {success}")
                    if success:
                        logger.debug(
                            f"Successfully cached A-share list with {len(a_share_data)} stocks"
                        )
                    stats["stock_list"] += 1
                else:
                    logger.debug("A股列表已存在于缓存中，跳过预热")

                # 预热美股列表
                us_stock_code = "list_US_stock"
                us_cached_data = await cache_service.get_stock_info(
                    us_stock_code, "US_stock"
                )
                logger.debug(
                    f"美股缓存检查结果: {us_cached_data is not None}, force={force}"
                )

                if force or not us_cached_data:
                    us_stocks = (
                        db.query(StockInfo)
                        .filter(
                            ~(
                                StockInfo.ts_code.like("%.SZ")
                                | StockInfo.ts_code.like("%.SH")
                            )
                        )
                        .all()
                    )
                    logger.debug(f"从数据库查询到 {len(us_stocks)} 只美股")

                    us_stock_data = [
                        {
                            "ts_code": stock.ts_code,
                            "name": stock.name,
                            "market_type": stock.market_type,
                        }
                        for stock in us_stocks
                    ]

                    success = await cache_service.set_stock_info(
                        us_stock_code, us_stock_data, "US_stock"
                    )
                    logger.debug(f"美股缓存设置结果: {success}")
                    if success:
                        logger.debug(
                            f"Successfully cached US stock list with {len(us_stock_data)} stocks"
                        )
                    stats["stock_list"] += 1
                else:
                    logger.debug("美股列表已存在于缓存中，跳过预热")

                logger.info(f"股票列表预热完成: {stats['stock_list']} 个列表")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"预热股票列表失败: {e}")
            stats["failed"] += 1

    async def _warm_hot_stocks_data(self, stats: dict[str, int], force: bool = False):
        """
        预热热点股票数据

        Args:
            stats: 统计信息字典
            force: 是否强制预热
        """
        try:
            # 获取热点股票列表
            hot_stocks = await self._get_hot_stocks()

            db = SessionLocal()
            try:
                for ts_code in hot_stocks:
                    # 预热不同时间间隔的数据
                    intervals = ["1d", "1w", "1m"]

                    for interval in intervals:
                        cache_key_suffix = f"{ts_code}_{interval}"

                        if force or not await cache_service.get_stock_daily_data(
                            ts_code, cache_key_suffix
                        ):
                            # 获取股票数据
                            stock_data = await self._fetch_stock_data(
                                db, ts_code, interval
                            )

                            if stock_data:
                                await cache_service.set_stock_daily_data(
                                    ts_code, cache_key_suffix, stock_data
                                )
                                stats["hot_stocks_data"] += 1

                logger.info(
                    f"热点股票数据预热完成: {stats['hot_stocks_data']} 个数据集"
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"预热热点股票数据失败: {e}")
            stats["failed"] += 1

    async def _warm_market_metrics(self, stats: dict[str, int], force: bool = False):
        """
        预热市场指标数据

        Args:
            stats: 统计信息字典
            force: 是否强制预热
        """
        try:
            db = SessionLocal()
            try:
                markets = ["A_share", "US_stock"]

                for market in markets:
                    market_code = f"market_metrics_{market}"

                    if force or not await cache_service.get_stock_metrics(
                        market_code, "latest", market
                    ):
                        # 获取市场指标
                        metrics = await self._fetch_market_metrics(db, market)

                        if metrics:
                            await cache_service.set_stock_metrics(
                                market_code, "latest", metrics, market
                            )
                            stats["market_metrics"] += 1

                logger.info(f"市场指标预热完成: {stats['market_metrics']} 个指标")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"预热市场指标失败: {e}")
            stats["failed"] += 1

    async def _warm_fundamental_data(self, stats: dict[str, int], force: bool = False):
        """
        预热基本面数据

        Args:
            stats: 统计信息字典
            force: 是否强制预热
        """
        try:
            # 获取hots股票的基本面数据
            hot_stocks = await self._get_hot_stocks(limit=50)  # 限制数量

            db = SessionLocal()
            try:
                for ts_code in hot_stocks:
                    if force or not await cache_service.get_stock_info(ts_code):
                        # 获取基本面数据
                        fundamental_data = await self._fetch_fundamental_data(
                            db, ts_code
                        )

                        if fundamental_data:
                            await cache_service.set_stock_info(
                                ts_code, fundamental_data
                            )
                            stats["fundamental_data"] += 1

                logger.info(f"基本面数据预热完成: {stats['fundamental_data']} 个数据")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"预热基本面数据失败: {e}")
            stats["failed"] += 1

    async def _get_hot_stocks(self, limit: int = 100) -> list[str]:
        """
        获取热点股票列表

        Args:
            limit: 返回数量限制

        Returns:
            List[str]: 热点股票代码列表
        """
        try:
            db = SessionLocal()
            try:
                # 基于交易量和价格变动获取热点股票
                recent_date = datetime.now().date() - timedelta(days=7)
                sql = text(
                    """
                    SELECT DISTINCT code
                    FROM daily_stock_metrics
                    WHERE date >= :recent_date AND volume IS NOT NULL
                    LIMIT :limit
                """
                )
                result = db.execute(sql, {"recent_date": recent_date, "limit": limit})
                hot_stocks = [row[0] for row in result.fetchall()]

                # 如果数据库中没有足够的数据，使用默认热点股票
                if len(hot_stocks) < 10:
                    default_hot_stocks = [
                        "000001.SZ",
                        "000002.SZ",
                        "600000.SH",
                        "600036.SH",
                        "600519.SH",
                        "AAPL",
                        "MSFT",
                        "GOOGL",
                        "AMZN",
                        "TSLA",
                    ]
                    hot_stocks.extend(default_hot_stocks)
                    hot_stocks = list(set(hot_stocks))[:limit]

                self.hot_stocks = set(hot_stocks)
                return hot_stocks

            finally:
                db.close()

        except Exception as e:
            logger.error(f"获取热点股票失败: {e}")
            # 返回默认热点股票
            return [
                "000001.SZ",
                "000002.SZ",
                "600000.SH",
                "600036.SH",
                "600519.SH",
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "TSLA",
            ]

    async def _fetch_stock_data(
        self, db: Session, ts_code: str, interval: str
    ) -> list[dict] | None:
        """
        获取股票数据

        Args:
            db: 数据库会话
            ts_code: 股票代码
            interval: 时间间隔

        Returns:
            Optional[List[Dict]]: 股票数据
        """
        try:
            # 根据间隔确定查询天数
            days_map = {"1d": 30, "1w": 90, "1m": 365}
            days = days_map.get(interval, 30)

            start_date = datetime.now().date() - timedelta(days=days)

            stock_data = (
                db.query(StockData)
                .filter(
                    StockData.ts_code == ts_code, StockData.trade_date >= start_date
                )
                .order_by(StockData.trade_date.desc())
                .limit(1000)
                .all()
            )

            if stock_data:
                return [
                    {
                        "trade_date": data.trade_date.isoformat(),
                        "open": float(data.open) if data.open else None,
                        "high": float(data.high) if data.high else None,
                        "low": float(data.low) if data.low else None,
                        "close": float(data.close) if data.close else None,
                        "volume": float(data.vol) if data.vol else None,
                        "amount": float(data.amount) if data.amount else None,
                    }
                    for data in stock_data
                ]

            return None

        except Exception as e:
            logger.error(f"获取股票数据失败 {ts_code}: {e}")
            return None

    async def _fetch_market_metrics(self, db: Session, market: str) -> dict | None:
        """
        获取市场指标

        Args:
            db: 数据库会话
            market: 市场类型

        Returns:
            Optional[Dict]: 市场指标数据
        """
        try:
            # 获取最新的市场指标
            latest_date = (
                db.query(func.max(DailyStockMetrics.date))
                .filter(DailyStockMetrics.market == market)
                .scalar()
            )

            if not latest_date:
                return None

            metrics = (
                db.query(DailyStockMetrics)
                .filter(
                    DailyStockMetrics.market == market,
                    DailyStockMetrics.date == latest_date,
                )
                .all()
            )

            if metrics:
                # 计算市场统计
                total_stocks = len(metrics)
                avg_pe = (
                    sum(m.pe_ratio for m in metrics if m.pe_ratio) / total_stocks
                    if total_stocks > 0
                    else 0
                )
                avg_pb = (
                    sum(m.pb_ratio for m in metrics if m.pb_ratio) / total_stocks
                    if total_stocks > 0
                    else 0
                )
                total_market_cap = (
                    sum(m.market_cap for m in metrics if m.market_cap) or 0
                )

                return {
                    "market": market,
                    "date": latest_date.isoformat(),
                    "total_stocks": total_stocks,
                    "avg_pe_ratio": round(avg_pe, 2),
                    "avg_pb_ratio": round(avg_pb, 2),
                    "total_market_cap": total_market_cap,
                    "timestamp": datetime.now().isoformat(),
                }

            return None

        except Exception as e:
            logger.error(f"获取市场指标失败 {market}: {e}")
            return None

    async def _fetch_fundamental_data(self, db: Session, ts_code: str) -> dict | None:
        """
        获取基本面数据

        Args:
            db: 数据库会话
            ts_code: 股票代码

        Returns:
            Optional[Dict]: 基本面数据
        """
        try:
            # 获取最新的基本面数据
            latest_metrics = (
                db.query(DailyStockMetrics)
                .filter(DailyStockMetrics.code == ts_code)
                .order_by(DailyStockMetrics.date.desc())
                .first()
            )

            if latest_metrics:
                return {
                    "ts_code": ts_code,
                    "date": latest_metrics.date.isoformat(),
                    "pe_ratio": latest_metrics.pe_ratio,
                    "pb_ratio": latest_metrics.pb_ratio,
                    "market_cap": latest_metrics.market_cap,
                    "volume": latest_metrics.volume,
                    "dividend_yield": latest_metrics.dividend_yield,
                    "timestamp": datetime.now().isoformat(),
                }

            return None

        except Exception as e:
            logger.error(f"获取基本面数据失败 {ts_code}: {e}")
            return None

    def _get_cache_ttl(self, interval: str) -> int:
        """
        根据时间间隔获取缓存TTL

        Args:
            interval: 时间间隔

        Returns:
            int: TTL秒数
        """
        ttl_map = {
            "1d": 3600,  # 1小时
            "1w": 6 * 3600,  # 6小时
            "1m": 24 * 3600,  # 24小时
        }
        return ttl_map.get(interval, 3600)

    async def incremental_update_stocks(self, ts_codes: list[str]) -> dict[str, Any]:
        """
        增量更新指定股票的缓存

        Args:
            ts_codes: 需要更新的股票代码列表

        Returns:
            Dict[str, Any]: 更新结果
        """
        updated_count = 0
        errors = []

        try:
            self.warming_in_progress = True

            for ts_code in ts_codes:
                try:
                    # 获取最新数据并更新缓存
                    with SessionLocal() as session:
                        # 获取股票基本信息
                        stock_info = (
                            session.query(StockInfo)
                            .filter(StockInfo.ts_code == ts_code)
                            .first()
                        )

                        if stock_info:
                            # 更新股票信息缓存
                            info_key = self.key_manager.generate_key(
                                "stock_info", ts_code
                            )
                            success = await cache_service.set_stock_info(
                                info_key,
                                {
                                    "ts_code": stock_info.ts_code,
                                    "name": stock_info.name,
                                    "market_type": stock_info.market_type,
                                },
                            )
                            if success:
                                logger.debug(
                                    f"Successfully cached stock info for {ts_code}"
                                )

                        # 获取最新交易数据
                        latest_data = (
                            session.query(StockData)
                            .filter(StockData.ts_code == ts_code)
                            .order_by(StockData.trade_date.desc())
                            .first()
                        )

                        if latest_data:
                            # 更新日线数据缓存
                            data_key = self.key_manager.generate_key(
                                "stock_daily", f"{ts_code}_1d"
                            )
                            success = await cache_service.set_stock_info(
                                data_key,
                                {
                                    "ts_code": latest_data.ts_code,
                                    "trade_date": latest_data.trade_date.isoformat(),
                                    "close": (
                                        float(latest_data.close)
                                        if latest_data.close
                                        else None
                                    ),
                                    "open": (
                                        float(latest_data.open)
                                        if latest_data.open
                                        else None
                                    ),
                                    "high": (
                                        float(latest_data.high)
                                        if latest_data.high
                                        else None
                                    ),
                                    "low": (
                                        float(latest_data.low)
                                        if latest_data.low
                                        else None
                                    ),
                                    "volume": (
                                        float(latest_data.vol)
                                        if latest_data.vol
                                        else None
                                    ),
                                },
                            )
                            if success:
                                logger.debug(
                                    f"Successfully cached daily data for {ts_code}"
                                )

                        updated_count += 1

                except Exception as e:
                    error_msg = f"Failed to update {ts_code}: {e!s}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue

            # 更新统计信息
            self.warming_stats["last_incremental_update"] = datetime.now()
            self.warming_stats["incremental_updates_count"] = (
                self.warming_stats.get("incremental_updates_count", 0) + 1
            )

            return {
                "status": "completed" if not errors else "partial",
                "updated_count": updated_count,
                "total_requested": len(ts_codes),
                "errors": errors,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            return {
                "status": "failed",
                "updated_count": updated_count,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            self.warming_in_progress = False

    async def get_warming_stats_async(self) -> dict[str, Any]:
        """
        获取预热统计信息（异步版本）

        Returns:
            Dict[str, Any]: 预热统计
        """
        return {
            **self.warming_stats,
            "hot_stocks_count": len(self.hot_stocks),
            "warming_in_progress": self.warming_in_progress,
            "hot_stocks": list(self.hot_stocks)[:20],  # 只返回前20个
        }

    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """
        根据模式失效缓存

        Args:
            pattern: 缓存键模式

        Returns:
            int: 失效的键数量
        """
        try:
            # CacheService 提供 clear_by_pattern 用于按模式清理缓存
            return cache_service.clear_by_pattern(pattern)
        except Exception as e:
            logger.error(f"失效缓存模式失败 {pattern}: {e}")
            return 0

    async def warm_specific_stocks(
        self, stock_codes: list[str], force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        预热指定股票的缓存

        Args:
            stock_codes: 股票代码列表
            force_refresh: 是否强制刷新

        Returns:
            Dict[str, Any]: 预热结果
        """
        try:
            results = {}
            for code in stock_codes:
                # 预热股票基本信息
                await self.warm_stock_info([code], force_refresh)
                # 预热股票数据
                await self.warm_stock_data([code], force_refresh)
                results[code] = "success"

            return {
                "status": "completed",
                "warmed_stocks": len(stock_codes),
                "results": results,
                "timestamp": datetime.now(),
            }
        except Exception as e:
            logger.error(f"预热指定股票缓存失败: {e}")
            return {"status": "failed", "error": str(e), "timestamp": datetime.now()}

    async def refresh_stock_cache(self, stock_codes: list[str]) -> dict[str, Any]:
        """
        刷新股票缓存

        Args:
            stock_codes: 股票代码列表

        Returns:
            Dict[str, Any]: 刷新结果
        """
        return await self.warm_specific_stocks(stock_codes, force_refresh=True)

    async def refresh_all_cache(self) -> dict[str, Any]:
        """
        刷新所有缓存

        Returns:
            Dict[str, Any]: 刷新结果
        """
        return await self.warm_cache(force=True)

    async def warm_cache(self, force: bool = False) -> dict[str, Any]:
        """
        预热缓存的主要方法

        Args:
            force: 是否强制预热

        Returns:
            Dict[str, Any]: 预热结果
        """
        try:
            # 获取热门股票
            hot_stocks = await self._get_hot_stocks()
            warmed_count = 0

            # 预热股票信息
            for stock_code in hot_stocks[:50]:  # 限制数量
                try:
                    await self.warm_stock_info([stock_code], force)
                    await self.warm_stock_data([stock_code], force)
                    warmed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to warm cache for {stock_code}: {e}")
                    continue

            return {
                "status": "completed",
                "warmed_count": warmed_count,
                "total_stocks": len(hot_stocks),
            }
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return {"status": "failed", "warmed_count": 0, "error": str(e)}

    async def warm_stock_info(
        self, stock_codes: list[str], force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        预热股票基本信息

        Args:
            stock_codes: 股票代码列表
            force_refresh: 是否强制刷新

        Returns:
            Dict[str, Any]: 预热结果
        """
        try:
            warmed_count = 0
            db = SessionLocal()
            try:
                for ts_code in stock_codes:
                    cache_key = self.key_manager.generate_key("stock_info", ts_code)

                    # 如果未强制刷新且缓存中已有数据，则跳过；否则从数据库加载并写入缓存
                    # 兼容同步/异步缓存接口
                    get_method = getattr(self.cache_service, "get", None)
                    has_cache = False
                    if get_method is not None:
                        if inspect.iscoroutinefunction(get_method):
                            has_cache = await get_method(cache_key)
                        else:
                            has_cache = get_method(cache_key)

                    if force_refresh or not has_cache:
                        # 从数据库获取股票信息
                        stock_info = (
                            db.query(StockInfo)
                            .filter(StockInfo.ts_code == ts_code)
                            .first()
                        )

                        if stock_info:
                            stock_data = {
                                "ts_code": stock_info.ts_code,
                                "name": stock_info.name,
                                "market_type": stock_info.market_type,
                                "industry": getattr(stock_info, "industry", None),
                                "list_date": getattr(stock_info, "list_date", None),
                            }
                            # 兼容同步/异步缓存接口
                            set_method = getattr(self.cache_service, "set", None)
                            if set_method is not None:
                                if inspect.iscoroutinefunction(set_method):
                                    await set_method(cache_key, stock_data)
                                else:
                                    set_method(cache_key, stock_data)
                            warmed_count += 1
                        else:
                            # 数据库无记录时，写入占位信息以保持缓存可用性
                            placeholder = {"ts_code": ts_code, "name": None}
                            set_method = getattr(self.cache_service, "set", None)
                            if set_method is not None:
                                if inspect.iscoroutinefunction(set_method):
                                    await set_method(cache_key, placeholder)
                                else:
                                    set_method(cache_key, placeholder)
                            warmed_count += 1
            finally:
                db.close()

            return {"status": "completed", "warmed_count": warmed_count}
        except Exception as e:
            logger.error(f"预热股票信息失败: {e}")
            return {"status": "failed", "error": str(e)}

    async def warm_stock_data(
        self, stock_codes: list[str], force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        预热股票数据

        Args:
            stock_codes: 股票代码列表
            force_refresh: 是否强制刷新

        Returns:
            Dict[str, Any]: 预热结果
        """
        try:
            warmed_count = 0
            db = SessionLocal()
            try:
                for ts_code in stock_codes:
                    for interval in ["1d", "1w", "1m"]:
                        cache_key = self.key_manager.generate_key(
                            "stock_daily", f"{ts_code}_{interval}"
                        )

                        # 如果未强制刷新且缓存中已有数据，则跳过；否则从数据库加载并写入缓存
                        get_method = getattr(self.cache_service, "get", None)
                        has_cache = False
                        if get_method is not None:
                            if inspect.iscoroutinefunction(get_method):
                                has_cache = await get_method(cache_key)
                            else:
                                has_cache = get_method(cache_key)

                        if force_refresh or not has_cache:
                            stock_data = await self._fetch_stock_data(
                                db, ts_code, interval
                            )

                            # 即使暂时无法从数据库获取，也写入占位数据，避免缓存缺口
                            ttl = self._get_cache_ttl(interval)
                            set_method = getattr(self.cache_service, "set", None)
                            if set_method is not None:
                                if inspect.iscoroutinefunction(set_method):
                                    await set_method(
                                        cache_key, stock_data or [], ttl=ttl
                                    )
                                else:
                                    set_method(cache_key, stock_data or [], ttl=ttl)
                            warmed_count += 1
            finally:
                db.close()

            return {"status": "completed", "warmed_count": warmed_count}
        except Exception as e:
            logger.error(f"预热股票数据失败: {e}")
            return {"status": "failed", "error": str(e)}

    def get_warming_stats(self) -> dict[str, Any]:
        """
        获取预热统计信息（同步版本）

        Returns:
            Dict[str, Any]: 预热统计
        """
        # 合并stats属性和warming_stats
        stats = getattr(self, "stats", {})
        return {
            **stats,
            **self.warming_stats,
            "hot_stocks_count": len(self.hot_stocks),
            "warming_in_progress": self.warming_in_progress,
            "hot_stocks": list(self.hot_stocks)[:20],  # 只返回前20个
        }

    def is_healthy(self) -> bool:
        """
        检查缓存预热服务是否健康

        Returns:
            bool: 健康状态
        """
        try:
            # 检查统计数据是否可用
            stats = self.get_warming_stats()
            return stats is not None
        except Exception:
            return False


# 全局缓存预热服务实例
cache_warming_service = CacheWarmingService()


# 便捷函数
async def warm_all_caches(force: bool = False) -> dict[str, Any]:
    """
    预热所有缓存的便捷函数

    Args:
        force: 是否强制预热

    Returns:
        Dict[str, Any]: 预热结果
    """
    return await cache_warming_service.warm_all_caches(force)


async def incremental_update_stocks(ts_codes: list[str]) -> dict[str, Any]:
    """
    增量更新股票缓存的便捷函数

    Args:
        ts_codes: 股票代码列表

    Returns:
        Dict[str, Any]: 更新结果
    """
    return await cache_warming_service.incremental_update_stocks(ts_codes)


def get_cache_warming_stats() -> dict[str, Any]:
    """
    获取缓存预热统计的便捷函数

    Returns:
        Dict[str, Any]: 预热统计
    """
    return cache_warming_service.get_warming_stats()
