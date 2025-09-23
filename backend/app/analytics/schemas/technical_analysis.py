from pydantic import BaseModel
from typing import List, Dict, Any
import datetime


class Indicator(BaseModel):
    name: str
    params: Dict[str, int] = {}


class TechnicalIndicatorsRequest(BaseModel):
    symbol: str
    interval: str
    start_date: str
    end_date: str
    indicators: List[Indicator]


class TechnicalIndicatorsResponse(BaseModel):
    symbol: str
    data: List[Dict[str, Any]]
