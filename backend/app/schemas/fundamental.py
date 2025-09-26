from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FundamentalDataBase(BaseModel):
    symbol: str
    market_cap: float | None = None
    pe_ratio: float | None = None
    dividend_yield: float | None = None
    eps: float | None = None
    beta: float | None = None
    gross_profit_margin: float | None = None
    net_profit_margin: float | None = None
    roe: float | None = None
    revenue_growth_rate: float | None = None
    net_profit_growth_rate: float | None = None
    debt_to_asset_ratio: float | None = None
    current_ratio: float | None = None


class FundamentalDataCreate(FundamentalDataBase):
    pass


class FundamentalDataInDB(FundamentalDataBase):
    id: int
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)
