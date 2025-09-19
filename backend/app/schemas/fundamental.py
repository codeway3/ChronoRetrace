from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


from typing import Union


class FundamentalDataBase(BaseModel):
    symbol: str
    market_cap: Union[float, None] = None
    pe_ratio: Union[float, None] = None
    dividend_yield: Union[float, None] = None
    eps: Union[float, None] = None
    beta: Union[float, None] = None
    gross_profit_margin: Union[float, None] = None
    net_profit_margin: Union[float, None] = None
    roe: Union[float, None] = None
    revenue_growth_rate: Union[float, None] = None
    net_profit_growth_rate: Union[float, None] = None
    debt_to_asset_ratio: Union[float, None] = None
    current_ratio: Union[float, None] = None


class FundamentalDataCreate(FundamentalDataBase):
    pass


class FundamentalDataInDB(FundamentalDataBase):
    id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)
