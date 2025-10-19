# !/usr/bin/env python3
"""
按资产类型分类的回溯测试API

提供按投资标的类型分类的回溯测试功能
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.analytics.services.strategy_service import BacktestService
from app.infrastructure.database.session import get_db
from app.schemas.asset_types import AssetFunction, AssetType, is_function_supported
from app.schemas.backtest import (
    BacktestOptimizationResponse,
    BacktestResult,
    GridStrategyConfig,
    GridStrategyOptimizeConfig,
)

router = APIRouter()
logger = logging.getLogger(__name__)

backtest_service = BacktestService(db=Depends(get_db))


@router.post("/backtest/{asset_type}/grid", response_model=BacktestResult)
async def backtest_grid_strategy_by_asset(
    asset_type: AssetType, config: GridStrategyConfig, db: Session = Depends(get_db)
):
    """
    按资产类型执行网格策略回溯测试

    Args:
        asset_type: 资产类型
        config: 网格策略配置
        db: 数据库会话

    Returns:
        BacktestResult: 回溯测试结果
    """
    # 检查资产类型是否支持回溯测试功能(避免在 try 中直接 raise)
    if not is_function_supported(asset_type, AssetFunction.BACKTEST):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"资产类型 {asset_type.value} 不支持回溯测试功能",
        )

    try:
        # 调用回溯测试服务
        result = await backtest_service.backtest_by_asset_type(
            asset_type=asset_type, config=config, db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"执行 {asset_type.value} 类型回溯测试时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行回溯测试时发生错误: {e!s}",
        ) from e
    else:
        logger.info(f"成功完成 {asset_type.value} 类型的网格策略回溯测试")
        return result


@router.post(
    "/backtest/{asset_type}/grid/optimize", response_model=BacktestOptimizationResponse
)
async def optimize_grid_strategy_by_asset(
    asset_type: AssetType,
    config: GridStrategyOptimizeConfig,
    db: Session = Depends(get_db),
):
    """
    按资产类型优化网格策略参数

    Args:
        asset_type: 资产类型
        config: 优化配置
        db: 数据库会话

    Returns:
        BacktestOptimizationResponse: 优化结果
    """
    # 检查资产类型是否支持回溯测试功能(避免在 try 中直接 raise)
    if not is_function_supported(asset_type, AssetFunction.BACKTEST):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"资产类型 {asset_type.value} 不支持回溯测试功能",
        )

    try:
        # 调用优化服务
        result = await backtest_service.optimize_by_asset_type(
            asset_type=asset_type, config=config, db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"优化 {asset_type.value} 类型策略参数时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"优化策略参数时发生错误: {e!s}",
        ) from e
    else:
        logger.info(f"成功完成 {asset_type.value} 类型的策略参数优化")
        return result


@router.get("/backtest/{asset_type}/strategies")
async def get_supported_strategies(asset_type: AssetType):
    """
    获取指定资产类型支持的回溯测试策略

    Returns:
        dict: 支持的策略列表
    """
    # 检查资产类型是否支持回溯测试功能(避免在 try 中直接 raise)
    if not is_function_supported(asset_type, AssetFunction.BACKTEST):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"资产类型 {asset_type.value} 不支持回溯测试功能",
        )

    # 直接获取并返回, 避免无意义的捕获后复抛
    strategies = backtest_service.get_supported_strategies(asset_type)
    return {"asset_type": asset_type.value, "strategies": strategies}


@router.get("/backtest/asset-types")
async def get_backtest_supported_asset_types():
    """
    获取支持回溯测试功能的资产类型列表

    Returns:
        dict: 支持的资产类型列表
    """
    try:
        supported_types = []
        for asset_type in AssetType:
            if is_function_supported(asset_type, AssetFunction.BACKTEST):
                supported_types.append(
                    {
                        "code": asset_type.value,
                        "name": asset_type.value.replace("-", " ").title(),
                    }
                )

        return {"supported_asset_types": supported_types, "total": len(supported_types)}

    except Exception as e:
        logger.exception("获取支持回溯测试的资产类型列表时发生错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取资产类型列表时发生错误: {e!s}",
        ) from e
