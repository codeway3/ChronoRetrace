from typing import Any

from pydantic import BaseModel


class Indicator(BaseModel):
    name: str
    params: dict[str, int] = {}


class TechnicalIndicatorsRequest(BaseModel):
    symbol: str
    interval: str
    start_date: str
    end_date: str
    indicators: list[Indicator]


class TechnicalIndicatorsResponse(BaseModel):
    symbol: str
    data: list[dict[str, Any]]
