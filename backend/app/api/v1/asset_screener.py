# !/usr/bin/env python3
"""
按资产类型分类的筛选器API

提供按投资标的类型分类的股票筛选功能
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.schemas.asset_types import (
    AssetFunction,
    AssetType,
    get_all_asset_types,  # Import the function directly
    is_function_supported,
)
from app.schemas.screener import ScreenerRequest, ScreenerResponse
from app.analytics.screener.screener_service import (
    screen_stocks,
)  # Import the function directly

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/screener/{asset_type}/stocks", response_model=ScreenerResponse)
async def screen_stocks_by_asset(
    asset_type: AssetType,
    request: ScreenerRequest,
    db: Session = Depends(get_db),
):
    """
    按投资标的类型筛选股票

    Args:
        asset_type: 资产类型
        request: 筛选条件
        db: 数据库会话

    Returns:
        ScreenerResponse: 筛选结果
    """
    # 检查资产类型是否支持筛选功能(避免在 try 中直接 raise)
    if not is_function_supported(asset_type, AssetFunction.SCREENER):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"资产类型 {asset_type.value} 不支持筛选功能",
        )

    try:
        # 调用筛选服务
        result = screen_stocks(db=db, criteria=request)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"筛选 {asset_type.value} 类型股票时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"筛选股票时发生错误: {e!s}",
        ) from e
    else:
        logger.info(
            f"成功筛选 {asset_type.value} 类型股票, 返回 {len(result.items)} 条结果"
        )
        return result


@router.get("/screener/asset-types")
async def get_supported_asset_types():
    """
    获取支持筛选功能的资产类型列表

    Returns:
        dict: 支持的资产类型列表
    """
    try:
        supported_types = [
            {"code": asset.code, "name": asset.name}
            for asset in get_all_asset_types()
            if is_function_supported(asset.code, AssetFunction.SCREENER)
        ]

        return {"supported_asset_types": supported_types, "total": len(supported_types)}

    except Exception as e:
        logger.exception("获取支持的资产类型列表时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取资产类型列表时发生错误: {e!s}",
        ) from e
