from __future__ import annotations

from datetime import date
from typing import Any, Union

from pydantic import BaseModel, ConfigDict


class StockDataBase(BaseModel):
    ts_code: str
    trade_date: date
    open: Union[float, None] = None
    high: Union[float, None] = None
    low: Union[float, None] = None
    close: Union[float, None] = None
    pre_close: Union[float, None] = None
    change: Union[float, None] = None
    pct_chg: Union[float, None] = None
    vol: Union[float, None] = None
    amount: Union[float, None] = None
    interval: str
    ma5: Union[float, None] = None
    ma10: Union[float, None] = None
    ma20: Union[float, None] = None
    ma60: Union[float, None] = None


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
    pe_ratio: Union[float, None] = None
    market_cap: Union[int, None] = None
    # Add other fields you want to display in the screener results
    model_config = ConfigDict(from_attributes=True)


class StockScreenerResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ScreenedStock]
