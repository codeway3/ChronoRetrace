# !/usr/bin/env python3
"""
按资产类型分类的筛选器API

提供按投资标的类型分类的股票筛选功能
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.schemas.asset_types import AssetFunction, AssetType, is_function_supported
from app.schemas.screener import ScreenerRequest, ScreenerResponse
from app.services.screener_service import screener_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/screener/{asset_type}/stocks", response_model=ScreenerResponse)
async def screen_stocks_by_asset(
    asset_type: AssetType,
    request: ScreenerRequest,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=1000, description="返回结果数量限制"),
    offset: int = Query(default=0, ge=0, description="结果偏移量"),
):
    """
    按投资标的类型筛选股票

    Args:
        asset_type: 资产类型
        request: 筛选条件
        db: 数据库会话
        limit: 返回结果数量限制
        offset: 结果偏移量

    Returns:
        ScreenerResponse: 筛选结果
    """
    try:
        # 检查资产类型是否支持筛选功能
        if not is_function_supported(asset_type, AssetFunction.SCREENER):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"资产类型 {asset_type.value} 不支持筛选功能",
            )

        # 调用筛选服务
        result = await screener_service.screen_stocks(
            asset_type=asset_type, criteria=request, limit=limit, offset=offset, db=db
        )

        logger.info(
            f"成功筛选 {asset_type.value} 类型股票，返回 {len(result.items)} 条结果"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"筛选 {asset_type.value} 类型股票时发生错误: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"筛选股票时发生错误: {e!s}",
        ) from e


@router.get("/screener/{asset_type}/config")
async def get_screener_criteria(asset_type: AssetType):
    """
    获取指定资产类型的筛选条件配置

    Args:
        asset_type: 资产类型

    Returns:
        dict: 筛选条件配置
    """
    try:
        # 检查资产类型是否支持筛选功能
        if not is_function_supported(asset_type, AssetFunction.SCREENER):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"资产类型 {asset_type.value} 不支持筛选功能",
            )

        # 获取筛选条件配置
        criteria_config = await screener_service.get_criteria_config(asset_type)

        return {"asset_type": asset_type.value, "criteria": criteria_config}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {asset_type.value} 筛选条件配置时发生错误: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取筛选条件配置时发生错误: {e!s}",
        ) from e


@router.get("/screener/asset-types")
async def get_supported_asset_types():
    """
    获取支持筛选功能的资产类型列表

    Returns:
        dict: 支持的资产类型列表
    """
    try:
        supported_types = []
        for asset_type in AssetType:
            if is_function_supported(asset_type, AssetFunction.SCREENER):
                supported_types.append(
                    {
                        "code": asset_type.value,
                        "name": asset_type.value.replace("-", " ").title(),
                    }
                )

        return {"supported_asset_types": supported_types, "total": len(supported_types)}

    except Exception as e:
        logger.error(f"获取支持的资产类型列表时发生错误: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取资产类型列表时发生错误: {e!s}",
        ) from e
