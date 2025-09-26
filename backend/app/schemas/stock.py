from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


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


class StockDataResponse(BaseModel):
    ts_code: str
    data: list[StockDataInDB]


# Stock Screener Schemas
class ScreenerCondition(BaseModel):
    field: str
    operator: str
    value: Any


class StockScreenerRequest(BaseModel):
    market: str = "A_share"
    conditions: list[ScreenerCondition]
    page: int = 1
    size: int = 20


class ScreenedStock(BaseModel):
    code: str
    name: str
    pe_ratio: float | None = None
    market_cap: int | None = None
    # Add other fields you want to display in the screener results
    model_config = ConfigDict(from_attributes=True)


class StockScreenerResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ScreenedStock]
