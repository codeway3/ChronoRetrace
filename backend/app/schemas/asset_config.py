from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    A_SHARE = "A_SHARE"
    US_STOCK = "US_STOCK"
    HK_STOCK = "HK_STOCK"
    CRYPTO = "CRYPTO"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    BONDS = "BONDS"
    FUNDS = "FUNDS"


class AssetConfigStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


# Asset Config Schemas
class AssetConfigBase(BaseModel):
    asset_type: AssetType
    name: str = Field(..., max_length=100, description="资产类型名称")
    display_name: str = Field(..., max_length=100, description="显示名称")
    description: str | None = Field(None, description="资产类型描述")
    supported_functions: list[str] = Field(..., description="支持的功能列表")
    screener_config: dict[str, Any] | None = Field(None, description="筛选器配置")
    backtest_config: dict[str, Any] | None = Field(None, description="回测配置")
    data_source_config: dict[str, Any] | None = Field(None, description="数据源配置")
    status: AssetConfigStatus = AssetConfigStatus.ACTIVE
    is_enabled: bool = Field(True, description="是否启用")
    sort_order: int | None = Field(None, description="排序顺序")


class AssetConfigCreate(AssetConfigBase):
    pass


class AssetConfigUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    display_name: str | None = Field(None, max_length=100)
    description: str | None = None
    supported_functions: list[str] | None = None
    screener_config: dict[str, Any] | None = None
    backtest_config: dict[str, Any] | None = None
    data_source_config: dict[str, Any] | None = None
    status: AssetConfigStatus | None = None
    is_enabled: bool | None = None
    sort_order: int | None = None


class AssetConfigResponse(AssetConfigBase):
    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# Asset Symbol Schemas
class AssetSymbolBase(BaseModel):
    asset_type: AssetType
    symbol: str = Field(..., max_length=50, description="标的代码")
    name: str = Field(..., max_length=200, description="标的名称")
    full_name: str | None = Field(None, max_length=500, description="完整名称")
    exchange: str | None = Field(None, max_length=50, description="交易所")
    sector: str | None = Field(None, max_length=100, description="行业/板块")
    industry: str | None = Field(None, max_length=100, description="细分行业")
    market_cap: str | None = Field(None, max_length=50, description="市值")
    currency: str | None = Field(None, max_length=10, description="交易货币")
    lot_size: int | None = Field(None, description="最小交易单位")
    tick_size: str | None = Field(None, max_length=20, description="最小价格变动单位")
    is_active: bool = Field(True, description="是否活跃")
    is_tradable: bool = Field(True, description="是否可交易")
    listing_date: datetime | None = Field(None, description="上市日期")
    delisting_date: datetime | None = Field(None, description="退市日期")
    metadata: dict[str, Any] | None = Field(None, description="扩展元数据")


class AssetSymbolCreate(AssetSymbolBase):
    pass


class AssetSymbolUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    full_name: str | None = Field(None, max_length=500)
    exchange: str | None = Field(None, max_length=50)
    sector: str | None = Field(None, max_length=100)
    industry: str | None = Field(None, max_length=100)
    market_cap: str | None = Field(None, max_length=50)
    currency: str | None = Field(None, max_length=10)
    lot_size: int | None = None
    tick_size: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    is_tradable: bool | None = None
    listing_date: datetime | None = None
    delisting_date: datetime | None = None
    metadata: dict[str, Any] | None = None


class AssetSymbolResponse(AssetSymbolBase):
    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# Asset Market Data Schemas
class AssetMarketDataBase(BaseModel):
    asset_type: AssetType
    symbol: str = Field(..., max_length=50)
    open_price: str | None = Field(None, max_length=20, description="开盘价")
    high_price: str | None = Field(None, max_length=20, description="最高价")
    low_price: str | None = Field(None, max_length=20, description="最低价")
    close_price: str | None = Field(None, max_length=20, description="收盘价")
    volume: str | None = Field(None, max_length=30, description="成交量")
    turnover: str | None = Field(None, max_length=30, description="成交额")
    change_amount: str | None = Field(None, max_length=20, description="涨跌额")
    change_percent: str | None = Field(None, max_length=10, description="涨跌幅")
    amplitude: str | None = Field(None, max_length=10, description="振幅")
    ma5: str | None = Field(None, max_length=20, description="5日均线")
    ma10: str | None = Field(None, max_length=20, description="10日均线")
    ma20: str | None = Field(None, max_length=20, description="20日均线")
    ma60: str | None = Field(None, max_length=20, description="60日均线")
    pe_ratio: str | None = Field(None, max_length=10, description="市盈率")
    pb_ratio: str | None = Field(None, max_length=10, description="市净率")
    ps_ratio: str | None = Field(None, max_length=10, description="市销率")
    dividend_yield: str | None = Field(None, max_length=10, description="股息率")
    open_interest: str | None = Field(None, max_length=30, description="持仓量")
    settlement_price: str | None = Field(None, max_length=20, description="结算价")
    implied_volatility: str | None = Field(
        None, max_length=10, description="隐含波动率"
    )
    market_cap_rank: int | None = Field(None, description="市值排名")
    circulating_supply: str | None = Field(
        None, max_length=30, description="流通供应量"
    )
    total_supply: str | None = Field(None, max_length=30, description="总供应量")
    trade_date: datetime = Field(..., description="交易日期")
    data_timestamp: datetime | None = Field(None, description="数据时间戳")


class AssetMarketDataCreate(AssetMarketDataBase):
    pass


class AssetMarketDataUpdate(BaseModel):
    open_price: str | None = Field(None, max_length=20)
    high_price: str | None = Field(None, max_length=20)
    low_price: str | None = Field(None, max_length=20)
    close_price: str | None = Field(None, max_length=20)
    volume: str | None = Field(None, max_length=30)
    turnover: str | None = Field(None, max_length=30)
    change_amount: str | None = Field(None, max_length=20)
    change_percent: str | None = Field(None, max_length=10)
    amplitude: str | None = Field(None, max_length=10)
    ma5: str | None = Field(None, max_length=20)
    ma10: str | None = Field(None, max_length=20)
    ma20: str | None = Field(None, max_length=20)
    ma60: str | None = Field(None, max_length=20)
    pe_ratio: str | None = Field(None, max_length=10)
    pb_ratio: str | None = Field(None, max_length=10)
    ps_ratio: str | None = Field(None, max_length=10)
    dividend_yield: str | None = Field(None, max_length=10)
    open_interest: str | None = Field(None, max_length=30)
    settlement_price: str | None = Field(None, max_length=20)
    implied_volatility: str | None = Field(None, max_length=10)
    market_cap_rank: int | None = None
    circulating_supply: str | None = Field(None, max_length=30)
    total_supply: str | None = Field(None, max_length=30)
    data_timestamp: datetime | None = None


class AssetMarketDataResponse(AssetMarketDataBase):
    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# Asset Screener Template Schemas
class AssetScreenerTemplateBase(BaseModel):
    asset_type: AssetType
    name: str = Field(..., max_length=100, description="模板名称")
    description: str | None = Field(None, description="模板描述")
    criteria: dict[str, Any] = Field(..., description="筛选条件配置")
    is_public: bool = Field(False, description="是否公开模板")
    is_system: bool = Field(False, description="是否系统模板")
    usage_count: int = Field(0, description="使用次数")
    created_by: int | None = Field(None, description="创建者ID")


class AssetScreenerTemplateCreate(AssetScreenerTemplateBase):
    pass


class AssetScreenerTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    criteria: dict[str, Any] | None = None
    is_public: bool | None = None
    usage_count: int | None = None


class AssetScreenerTemplateResponse(AssetScreenerTemplateBase):
    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# Asset Backtest Template Schemas
class AssetBacktestTemplateBase(BaseModel):
    asset_type: AssetType
    name: str = Field(..., max_length=100, description="模板名称")
    description: str | None = Field(None, description="模板描述")
    strategy_type: str = Field(..., max_length=50, description="策略类型")
    strategy_config: dict[str, Any] = Field(..., description="策略配置")
    backtest_config: dict[str, Any] | None = Field(None, description="回测配置")
    is_public: bool = Field(False, description="是否公开模板")
    is_system: bool = Field(False, description="是否系统模板")
    usage_count: int = Field(0, description="使用次数")
    created_by: int | None = Field(None, description="创建者ID")


class AssetBacktestTemplateCreate(AssetBacktestTemplateBase):
    pass


class AssetBacktestTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    strategy_type: str | None = Field(None, max_length=50)
    strategy_config: dict[str, Any] | None = None
    backtest_config: dict[str, Any] | None = None
    is_public: bool | None = None
    usage_count: int | None = None


class AssetBacktestTemplateResponse(AssetBacktestTemplateBase):
    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
