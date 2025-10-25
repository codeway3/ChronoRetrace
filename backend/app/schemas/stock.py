from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.screener import ScreenerCondition

if TYPE_CHECKING:
    from datetime import date


class StockDataBase(BaseModel):
    ts_code: str
    trade_date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    pre_close: float | None = None
    change: float | None = None
    pct_chg: float | None = None
    vol: float | None = None
    amount: float | None = None
    interval: str
    ma5: float | None = None
    ma10: float | None = None
    ma20: float | None = None
    ma60: float | None = None


class StockDataCreate(StockDataBase):
    pass


class StockDataInDB(StockDataBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class StockInfo(BaseModel):
    ts_code: str
    name: str
    # Ensure ORM objects (SQLAlchemy) can be parsed directly
    model_config = ConfigDict(from_attributes=True)


class StockDataResponse(BaseModel):
    ts_code: str
    data: list[StockDataInDB]


# Legacy compatibility for screener tests


class StockScreenerRequest(BaseModel):
    """兼容旧版测试的筛选请求模型。

    旧版使用 market 字段代替新 schema 中的 asset_type。
    """

    market: str = Field(..., description="资产类型/市场")
    conditions: list[ScreenerCondition] = Field(default=[], description="筛选条件列表")
    sort_by: str | None = Field(None, description="排序字段")
    sort_order: str = Field("desc", description="排序方向: asc, desc")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


# Explicitly export for tests that import from app.schemas.stock
__all__ = [
    "ScreenerCondition",
    "StockDataBase",
    "StockDataCreate",
    "StockDataInDB",
    "StockDataResponse",
    "StockInfo",
    "StockScreenerRequest",
]
