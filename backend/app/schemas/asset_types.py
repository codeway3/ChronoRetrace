# !/usr/bin/env python3
"""
资产类型枚举和相关数据模型

定义投资标的类型枚举，支持按资产类型分类的API设计
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    """投资标的类型枚举"""

    A_SHARE = "a-share"
    US_STOCK = "us-stock"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"
    FUTURES = "futures"
    OPTIONS = "options"


class AssetCategory(str, Enum):
    """资产功能分类枚举"""

    QUOTES = "quotes"  # 行情数据
    TOOLS = "tools"  # 分析工具


class AssetFunction(str, Enum):
    """具体功能枚举"""

    REALTIME = "realtime"  # 实时行情
    INDUSTRIES = "industries"  # 行业分析（仅A股）
    SCREENER = "screener"  # 筛选器
    BACKTEST = "backtest"  # 回溯测试


class AssetTypeConfig(BaseModel):
    """资产类型配置"""

    code: AssetType
    name: str
    description: str
    enabled: bool = True
    supported_functions: list[AssetFunction] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssetTypeResponse(BaseModel):
    """资产类型响应模型"""

    asset_types: list[AssetTypeConfig]
    total: int


# 预定义的资产类型配置
ASSET_TYPE_CONFIGS: dict[AssetType, AssetTypeConfig] = {
    AssetType.A_SHARE: AssetTypeConfig(
        code=AssetType.A_SHARE,
        name="A股市场",
        description="中国A股市场数据和分析工具",
        enabled=True,
        supported_functions=[
            AssetFunction.REALTIME,
            AssetFunction.INDUSTRIES,
            AssetFunction.SCREENER,
            AssetFunction.BACKTEST,
        ],
    ),
    AssetType.US_STOCK: AssetTypeConfig(
        code=AssetType.US_STOCK,
        name="美股市场",
        description="美国股票市场数据和分析工具",
        enabled=True,
        supported_functions=[
            AssetFunction.REALTIME,
            AssetFunction.SCREENER,
            AssetFunction.BACKTEST,
        ],
    ),
    AssetType.CRYPTO: AssetTypeConfig(
        code=AssetType.CRYPTO,
        name="加密货币",
        description="加密货币市场数据和分析工具",
        enabled=True,
        supported_functions=[
            AssetFunction.REALTIME,
            AssetFunction.SCREENER,
            AssetFunction.BACKTEST,
        ],
    ),
    AssetType.COMMODITIES: AssetTypeConfig(
        code=AssetType.COMMODITIES,
        name="大宗商品",
        description="大宗商品市场数据和分析工具",
        enabled=True,
        supported_functions=[
            AssetFunction.REALTIME,
            AssetFunction.SCREENER,
            AssetFunction.BACKTEST,
        ],
    ),
    AssetType.FUTURES: AssetTypeConfig(
        code=AssetType.FUTURES,
        name="期货市场",
        description="期货市场数据和分析工具",
        enabled=True,
        supported_functions=[
            AssetFunction.REALTIME,
            AssetFunction.SCREENER,
            AssetFunction.BACKTEST,
        ],
    ),
    AssetType.OPTIONS: AssetTypeConfig(
        code=AssetType.OPTIONS,
        name="期权市场",
        description="期权市场数据和分析工具",
        enabled=True,
        supported_functions=[
            AssetFunction.REALTIME,
            AssetFunction.SCREENER,
            AssetFunction.BACKTEST,
        ],
    ),
}


def get_asset_type_config(asset_type: AssetType) -> AssetTypeConfig | None:
    """获取资产类型配置"""
    return ASSET_TYPE_CONFIGS.get(asset_type)


def get_all_asset_types() -> list[AssetTypeConfig]:
    """获取所有资产类型配置"""
    return list(ASSET_TYPE_CONFIGS.values())


def is_function_supported(asset_type: AssetType, function: AssetFunction) -> bool:
    """检查资产类型是否支持指定功能"""
    config = get_asset_type_config(asset_type)
    return config is not None and function in config.supported_functions
