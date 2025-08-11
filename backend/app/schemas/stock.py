from pydantic import BaseModel, ConfigDict
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
