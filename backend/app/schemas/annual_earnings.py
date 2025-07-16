from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AnnualEarningsBase(BaseModel):
    symbol: str
    year: int
    net_profit: Optional[float] = None

class AnnualEarningsCreate(AnnualEarningsBase):
    pass

class AnnualEarningsInDB(AnnualEarningsBase):
    id: int
    last_updated: datetime

    class Config:
        from_attributes = True
