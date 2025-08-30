from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import List, Optional, Any

class StockDataBase(BaseModel):
    ts_code: str
    trade_date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    pre_close: Optional[float] = None
    change: Optional[float] = None
    pct_chg: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    interval: str
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None

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
    data: List[StockDataInDB]


# Stock Screener Schemas
class ScreenerCondition(BaseModel):
    field: str
    operator: str
    value: Any

class StockScreenerRequest(BaseModel):
    market: str = 'A_share'
    conditions: List[ScreenerCondition]
    page: int = 1
    size: int = 20

class ScreenedStock(BaseModel):
    code: str
    name: str
    pe_ratio: Optional[float] = None
    market_cap: Optional[int] = None
    # Add other fields you want to display in the screener results
    model_config = ConfigDict(from_attributes=True)


class StockScreenerResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[ScreenedStock]
