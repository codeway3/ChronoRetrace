from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FundamentalDataBase(BaseModel):
    symbol: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    eps: Optional[float] = None
    beta: Optional[float] = None
    gross_profit_margin: Optional[float] = None
    net_profit_margin: Optional[float] = None
    roe: Optional[float] = None
    revenue_growth_rate: Optional[float] = None
    net_profit_growth_rate: Optional[float] = None
    debt_to_asset_ratio: Optional[float] = None
    current_ratio: Optional[float] = None


class FundamentalDataCreate(FundamentalDataBase):
    pass


class FundamentalDataInDB(FundamentalDataBase):
    id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)
