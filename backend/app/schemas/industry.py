from __future__ import annotations

from pydantic import BaseModel, ConfigDict


from typing import Union

class ConstituentStock(BaseModel):
    """
    Represents a single constituent stock within an industry.
    """

    stock_code: str
    stock_name: str
    latest_price: Union[float, None] = None
    pct_change: Union[float, None] = None
    pe_ratio: Union[float, None] = None
    turnover_rate: Union[float, None] = None

    model_config = ConfigDict(from_attributes=True)
