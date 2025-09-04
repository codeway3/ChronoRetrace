from typing import Optional

from pydantic import BaseModel, ConfigDict


class ConstituentStock(BaseModel):
    """
    Represents a single constituent stock within an industry.
    """

    stock_code: str
    stock_name: str
    latest_price: Optional[float] = None
    pct_change: Optional[float] = None
    pe_ratio: Optional[float] = None
    turnover_rate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
