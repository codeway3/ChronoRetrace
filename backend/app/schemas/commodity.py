from pydantic import BaseModel


class CommodityData(BaseModel):
    symbol: str
    data: list[dict]
