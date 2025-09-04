from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AnnualEarningsBase(BaseModel):
    symbol: str
    year: int
    net_profit: Optional[float] = None


class AnnualEarningsCreate(AnnualEarningsBase):
    pass


class AnnualEarningsInDB(AnnualEarningsBase):
    id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)
