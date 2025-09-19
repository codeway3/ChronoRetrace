from __future__ import annotations

# !/usr/bin/env python3
"""
带缓存的股票API路由
使用新的缓存服务层提供高性能的股票数据API
"""

from typing import Union

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.data.managers import data_manager as data_fetcher
from app.infrastructure.database.session import get_db
from app.schemas.corporate_action import CorporateActionResponse
from app.schemas.stock import StockDataBase, StockInfo
from app.services import stock_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list/all", response_model=list[StockInfo])
async def get_all_stock_list_cached(
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    db: Session = Depends(get_db),
):
    """

from __future__ import annotations

获取股票列表（带缓存）

    使用多级缓存提供高性能的股票列表查询
    """
    try:
        return await stock_service.get_stock_list(db, market_type)
    except Exception as e:
        logger.error(f"Error in get_all_stock_list_cached: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/list/refresh", status_code=200)
async def refresh_stock_list_cached(
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    db: Session = Depends(get_db),
):
    """刷新股票列表缓存

    强制更新股票列表并清除相关缓存
    """
    try:
        result = await stock_service.refresh_stock_list(db, market_type)
        return result
    except Exception as e:
        logger.error(f"Error in refresh_stock_list_cached: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/data", response_model=list[StockDataBase])
async def get_stock_data_cached(
    stock_code: str,
    interval: str = Query(
        "daily", enum=["minute", "5day", "daily", "weekly", "monthly"]
    ),
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    trade_date: Union[date, None] = Query(
        None, description="Date for 'minute' or '5day' interval, format YYYY-MM-DD"
    ),
):
    """获取股票数据（带缓存）

    使用智能缓存策略：
    - 分钟级和5日线数据：不缓存（实时性要求高）
    - 日线及以上级别：使用Redis缓存
    """
    try:
        return await stock_service.get_stock_data(
            stock_code=stock_code,
            interval=interval,
            market_type=market_type,
            trade_date=trade_date,
        )
    except Exception as e:
        logger.error(f"Error in get_stock_data_cached: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{symbol}/sync", status_code=202)
async def sync_data_for_symbol_cached(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """同步股票数据并失效缓存

    触发后台任务同步数据，并自动失效相关缓存
    """
    try:
        resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
        if not resolved_symbol:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

        # 添加后台同步任务
        background_tasks.add_task(data_fetcher.sync_financial_data, resolved_symbol)

        # 失效相关缓存
        background_tasks.add_task(
            stock_service.invalidate_stock_cache,
            resolved_symbol,
            "A_share",  # 默认市场类型，可以根据需要调整
        )

        return {
            "message": f"Data synchronization for {resolved_symbol} has been started in the background.",
            "cache_invalidated": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sync_data_for_symbol_cached: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{symbol}/fundamentals")
async def get_fundamental_data_cached(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """获取基本面数据（带缓存）

    使用多级缓存提供高性能的基本面数据查询
    如果数据过期或缺失，会触发后台同步
    """
    try:
        # 尝试从缓存获取数据
        fundamental_data = await stock_service.get_fundamental_data(db, symbol)

        # 检查数据是否过期或缺失
        if not fundamental_data or (
            hasattr(fundamental_data, "last_updated")
            and fundamental_data.last_updated
            and (datetime.utcnow() - fundamental_data.last_updated)
            > timedelta(hours=24)
        ):
            # 触发后台同步
            resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
            if resolved_symbol:
                background_tasks.add_task(
                    data_fetcher.sync_financial_data, resolved_symbol
                )

                # 如果没有数据，返回202状态
                if not fundamental_data:
                    return JSONResponse(
                        status_code=status.HTTP_202_ACCEPTED,
                        content={
                            "message": f"Fundamental data for {resolved_symbol} is being synced. Please try again in a moment."
                        },
                    )

        return fundamental_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_fundamental_data_cached: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{symbol}/corporate-actions")
async def get_corporate_actions_cached(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """获取公司行动数据（带缓存）

    使用多级缓存提供高性能的公司行动数据查询
    """
    try:
        actions = await stock_service.get_corporate_actions(db, symbol)

        if not actions:
            # 触发后台同步
            resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
            if resolved_symbol:
                background_tasks.add_task(
                    data_fetcher.sync_financial_data, resolved_symbol
                )

        return CorporateActionResponse(symbol=symbol, actions=actions)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_corporate_actions_cached: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{symbol}/annual-earnings")
async def get_annual_earnings_cached(
    symbol: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """获取年度收益数据（带缓存）

    使用多级缓存提供高性能的年度收益数据查询
    """
    try:
        earnings = await stock_service.get_annual_earnings(db, symbol)

        if not earnings:
            # 触发后台同步
            resolved_symbol = data_fetcher.resolve_symbol(db, symbol)
            if resolved_symbol:
                background_tasks.add_task(
                    data_fetcher.sync_financial_data, resolved_symbol
                )

        return earnings

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_annual_earnings_cached: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# 缓存管理API
@router.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息

    返回详细的缓存性能指标和统计数据
    """
    try:
        stats = await stock_service.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cache/invalidate/{stock_code}")
async def invalidate_stock_cache(
    stock_code: str, market_type: str = Query("A_share", enum=["A_share", "US_stock"])
):
    """手动失效股票缓存

    用于数据更新后手动清理相关缓存
    """
    try:
        await stock_service.invalidate_stock_cache(stock_code, market_type)
        return {
            "message": f"Cache invalidated for stock: {stock_code}",
            "market_type": market_type,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error invalidating cache for {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/cache/preload")
async def preload_hot_stocks(
    market_type: str = Query("A_share", enum=["A_share", "US_stock"]),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """预加载热门股票数据

    预加载指定数量的热门股票数据到缓存中
    """
    try:
        await stock_service.preload_hot_stocks(db, market_type, limit)
        return {
            "message": f"Preload completed for {limit} stocks in {market_type}",
            "market_type": market_type,
            "limit": limit,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error preloading hot stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def health_check():
    """服务健康检查

    检查股票服务和缓存系统的健康状态
    """
    try:
        health_status = await stock_service.health_check()

        # 根据健康状态设置HTTP状态码
        status_code = 200
        if health_status.get("overall_status") == "degraded":
            status_code = 206  # Partial Content
        elif health_status.get("overall_status") == "unhealthy":
            status_code = 503  # Service Unavailable

        return JSONResponse(status_code=status_code, content=health_status)

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )


@router.get("/trade-date")
def get_trade_date(offset: int = 0) -> str:
    """获取交易日期

    Args:
        offset: 日期偏移量（负数表示过去的日期）

    Returns:
        格式化的交易日期字符串
    """
    target_date = datetime.now() + timedelta(days=offset)
    return target_date.strftime("%Y-%m-%d")
