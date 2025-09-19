from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


from typing import Union


class AnnualEarningsBase(BaseModel):
    symbol: str
    year: int
    net_profit: Union[float, None] = None


class AnnualEarningsCreate(AnnualEarningsBase):
    pass


class AnnualEarningsInDB(AnnualEarningsBase):
    id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)
