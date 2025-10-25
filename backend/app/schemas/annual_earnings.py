from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from datetime import datetime


class AnnualEarningsBase(BaseModel):
    symbol: str
    year: int
    net_profit: float | None = None


class AnnualEarningsCreate(AnnualEarningsBase):
    pass


class AnnualEarningsInDB(AnnualEarningsBase):
    id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)
