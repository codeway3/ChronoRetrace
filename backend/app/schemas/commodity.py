from typing import List, Dict
from pydantic import BaseModel


class CommodityData(BaseModel):
    symbol: str
    data: List[Dict]
