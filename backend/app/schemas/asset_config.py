from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

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
    description: Optional[str] = Field(None, description="资产类型描述")
    supported_functions: List[str] = Field(..., description="支持的功能列表")
    screener_config: Optional[Dict[str, Any]] = Field(None, description="筛选器配置")
    backtest_config: Optional[Dict[str, Any]] = Field(None, description="回测配置")
    data_source_config: Optional[Dict[str, Any]] = Field(None, description="数据源配置")
    status: AssetConfigStatus = AssetConfigStatus.ACTIVE
    is_enabled: bool = Field(True, description="是否启用")
    sort_order: Optional[int] = Field(None, description="排序顺序")


class AssetConfigCreate(AssetConfigBase):
    pass


class AssetConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    supported_functions: Optional[List[str]] = None
    screener_config: Optional[Dict[str, Any]] = None
    backtest_config: Optional[Dict[str, Any]] = None
    data_source_config: Optional[Dict[str, Any]] = None
    status: Optional[AssetConfigStatus] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class AssetConfigResponse(AssetConfigBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


    class Config:
        from_attributes = True

# Asset Symbol Schemas
class AssetSymbolBase(BaseModel):
    asset_type: AssetType
    symbol: str = Field(..., max_length=50, description="标的代码")
    name: str = Field(..., max_length=200, description="标的名称")
    full_name: Optional[str] = Field(None, max_length=500, description="完整名称")
    exchange: Optional[str] = Field(None, max_length=50, description="交易所")
    sector: Optional[str] = Field(None, max_length=100, description="行业/板块")
    industry: Optional[str] = Field(None, max_length=100, description="细分行业")
    market_cap: Optional[str] = Field(None, max_length=50, description="市值")
    currency: Optional[str] = Field(None, max_length=10, description="交易货币")
    lot_size: Optional[int] = Field(None, description="最小交易单位")
    tick_size: Optional[str] = Field(None, max_length=20, description="最小价格变动单位")
    is_active: bool = Field(True, description="是否活跃")
    is_tradable: bool = Field(True, description="是否可交易")
    listing_date: Optional[datetime] = Field(None, description="上市日期")
    delisting_date: Optional[datetime] = Field(None, description="退市日期")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class AssetSymbolCreate(AssetSymbolBase):
    pass


class AssetSymbolUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    full_name: Optional[str] = Field(None, max_length=500)
    exchange: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market_cap: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=10)
    lot_size: Optional[int] = None
    tick_size: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    is_tradable: Optional[bool] = None
    listing_date: Optional[datetime] = None
    delisting_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetSymbolResponse(AssetSymbolBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


    class Config:
        from_attributes = True

# Asset Market Data Schemas
class AssetMarketDataBase(BaseModel):
    asset_type: AssetType
    symbol: str = Field(..., max_length=50)
    open_price: Optional[str] = Field(None, max_length=20, description="开盘价")
    high_price: Optional[str] = Field(None, max_length=20, description="最高价")
    low_price: Optional[str] = Field(None, max_length=20, description="最低价")
    close_price: Optional[str] = Field(None, max_length=20, description="收盘价")
    volume: Optional[str] = Field(None, max_length=30, description="成交量")
    turnover: Optional[str] = Field(None, max_length=30, description="成交额")
    change_amount: Optional[str] = Field(None, max_length=20, description="涨跌额")
    change_percent: Optional[str] = Field(None, max_length=10, description="涨跌幅")
    amplitude: Optional[str] = Field(None, max_length=10, description="振幅")
    ma5: Optional[str] = Field(None, max_length=20, description="5日均线")
    ma10: Optional[str] = Field(None, max_length=20, description="10日均线")
    ma20: Optional[str] = Field(None, max_length=20, description="20日均线")
    ma60: Optional[str] = Field(None, max_length=20, description="60日均线")
    pe_ratio: Optional[str] = Field(None, max_length=10, description="市盈率")
    pb_ratio: Optional[str] = Field(None, max_length=10, description="市净率")
    ps_ratio: Optional[str] = Field(None, max_length=10, description="市销率")
    dividend_yield: Optional[str] = Field(None, max_length=10, description="股息率")
    open_interest: Optional[str] = Field(None, max_length=30, description="持仓量")
    settlement_price: Optional[str] = Field(None, max_length=20, description="结算价")
    implied_volatility: Optional[str] = Field(None, max_length=10, description="隐含波动率")
    market_cap_rank: Optional[int] = Field(None, description="市值排名")
    circulating_supply: Optional[str] = Field(None, max_length=30, description="流通供应量")
    total_supply: Optional[str] = Field(None, max_length=30, description="总供应量")
    trade_date: datetime = Field(..., description="交易日期")
    data_timestamp: Optional[datetime] = Field(None, description="数据时间戳")


class AssetMarketDataCreate(AssetMarketDataBase):
    pass


class AssetMarketDataUpdate(BaseModel):
    open_price: Optional[str] = Field(None, max_length=20)
    high_price: Optional[str] = Field(None, max_length=20)
    low_price: Optional[str] = Field(None, max_length=20)
    close_price: Optional[str] = Field(None, max_length=20)
    volume: Optional[str] = Field(None, max_length=30)
    turnover: Optional[str] = Field(None, max_length=30)
    change_amount: Optional[str] = Field(None, max_length=20)
    change_percent: Optional[str] = Field(None, max_length=10)
    amplitude: Optional[str] = Field(None, max_length=10)
    ma5: Optional[str] = Field(None, max_length=20)
    ma10: Optional[str] = Field(None, max_length=20)
    ma20: Optional[str] = Field(None, max_length=20)
    ma60: Optional[str] = Field(None, max_length=20)
    pe_ratio: Optional[str] = Field(None, max_length=10)
    pb_ratio: Optional[str] = Field(None, max_length=10)
    ps_ratio: Optional[str] = Field(None, max_length=10)
    dividend_yield: Optional[str] = Field(None, max_length=10)
    open_interest: Optional[str] = Field(None, max_length=30)
    settlement_price: Optional[str] = Field(None, max_length=20)
    implied_volatility: Optional[str] = Field(None, max_length=10)
    market_cap_rank: Optional[int] = None
    circulating_supply: Optional[str] = Field(None, max_length=30)
    total_supply: Optional[str] = Field(None, max_length=30)
    data_timestamp: Optional[datetime] = None


class AssetMarketDataResponse(AssetMarketDataBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


    class Config:
        from_attributes = True

# Asset Screener Template Schemas
class AssetScreenerTemplateBase(BaseModel):
    asset_type: AssetType
    name: str = Field(..., max_length=100, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    criteria: Dict[str, Any] = Field(..., description="筛选条件配置")
    is_public: bool = Field(False, description="是否公开模板")
    is_system: bool = Field(False, description="是否系统模板")
    usage_count: int = Field(0, description="使用次数")
    created_by: Optional[int] = Field(None, description="创建者ID")


class AssetScreenerTemplateCreate(AssetScreenerTemplateBase):
    pass


class AssetScreenerTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    usage_count: Optional[int] = None


class AssetScreenerTemplateResponse(AssetScreenerTemplateBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


    class Config:
        from_attributes = True

# Asset Backtest Template Schemas
class AssetBacktestTemplateBase(BaseModel):
    asset_type: AssetType
    name: str = Field(..., max_length=100, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    strategy_type: str = Field(..., max_length=50, description="策略类型")
    strategy_config: Dict[str, Any] = Field(..., description="策略配置")
    backtest_config: Optional[Dict[str, Any]] = Field(None, description="回测配置")
    is_public: bool = Field(False, description="是否公开模板")
    is_system: bool = Field(False, description="是否系统模板")
    usage_count: int = Field(0, description="使用次数")
    created_by: Optional[int] = Field(None, description="创建者ID")


class AssetBacktestTemplateCreate(AssetBacktestTemplateBase):
    pass


class AssetBacktestTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    strategy_type: Optional[str] = Field(None, max_length=50)
    strategy_config: Optional[Dict[str, Any]] = None
    backtest_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    usage_count: Optional[int] = None


class AssetBacktestTemplateResponse(AssetBacktestTemplateBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


    class Config:
        from_attributes = True
