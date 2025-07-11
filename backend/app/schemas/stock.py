from pydantic import BaseModel
from datetime import date
from typing import List, Optional

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

class StockDataCreate(StockDataBase):
    pass

class StockDataInDB(StockDataBase):
    id: int

    class Config:
        from_attributes = True

class StockInfo(BaseModel):
    ts_code: str
    name: str

class StockDataResponse(BaseModel):
    ts_code: str
    data: List[StockDataInDB]
