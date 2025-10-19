"""
筛选器相关的Pydantic schemas
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScreenerCondition(BaseModel):
    """筛选条件"""

    field: str = Field(..., description="筛选字段")
    operator: str = Field(..., description="操作符: >, <, >=, <=, =, !=, in, not_in")
    value: Any = Field(..., description="筛选值")


class ScreenerRequest(BaseModel):
    """筛选器请求"""

    asset_type: str = Field(..., description="资产类型")
    conditions: list[ScreenerCondition] = Field(default=[], description="筛选条件列表")
    sort_by: str | None = Field(None, description="排序字段")
    sort_order: str = Field("desc", description="排序方向: asc, desc")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


class ScreenerResultItem(BaseModel):
    """筛选结果项"""

    # 兼容旧字段：支持 code 和 symbol，优先使用 code
    code: str | None = Field(None, description="标的代码（兼容旧字段）")
    symbol: str | None = Field(None, description="标的代码（新字段）")
    name: str = Field(..., description="标的名称")
    market: str | None = Field(None, description="市场")
    sector: str | None = Field(None, description="行业")
    market_cap: float | None = Field(None, description="市值")
    price: float | None = Field(None, description="当前价格")
    change_percent: float | None = Field(None, description="涨跌幅")
    volume: int | None = Field(None, description="成交量")
    pe_ratio: float | None = Field(None, description="市盈率")
    pb_ratio: float | None = Field(None, description="市净率")
    dividend_yield: float | None = Field(None, description="股息率")
    additional_data: dict[str, Any] | None = Field(None, description="额外数据")


class ScreenerResponse(BaseModel):
    """筛选器响应"""

    items: list[ScreenerResultItem] = Field(..., description="筛选结果列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    filters_applied: list[ScreenerCondition] = Field(..., description="应用的筛选条件")


class ScreenerTemplateBase(BaseModel):
    """筛选器模板基础模型"""

    name: str = Field(..., description="模板名称")
    description: str | None = Field(None, description="模板描述")
    asset_type: str = Field(..., description="资产类型")
    conditions: list[ScreenerCondition] = Field(..., description="筛选条件")
    sort_by: str | None = Field(None, description="排序字段")
    sort_order: str = Field("desc", description="排序方向")
    is_public: bool = Field(False, description="是否公开")


class ScreenerTemplateCreate(ScreenerTemplateBase):
    """创建筛选器模板"""

    pass


class ScreenerTemplateUpdate(BaseModel):
    """更新筛选器模板"""

    name: str | None = Field(None, description="模板名称")
    description: str | None = Field(None, description="模板描述")
    conditions: list[ScreenerCondition] | None = Field(None, description="筛选条件")
    sort_by: str | None = Field(None, description="排序字段")
    sort_order: str | None = Field(None, description="排序方向")
    is_public: bool | None = Field(None, description="是否公开")


class ScreenerTemplateResponse(ScreenerTemplateBase):
    """筛选器模板响应"""

    id: int = Field(..., description="模板ID")
    user_id: int = Field(..., description="创建用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class ScreenerStats(BaseModel):
    """筛选器统计信息"""

    total_assets: int = Field(..., description="总资产数量")
    filtered_count: int = Field(..., description="筛选后数量")
    filter_ratio: float = Field(..., description="筛选比例")
    top_sectors: list[dict[str, Any]] = Field(..., description="热门行业")
    price_range: dict[str, float] = Field(..., description="价格范围")
    market_cap_range: dict[str, float] = Field(..., description="市值范围")
