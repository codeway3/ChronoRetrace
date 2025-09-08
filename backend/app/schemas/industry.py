
from pydantic import BaseModel, ConfigDict


class ConstituentStock(BaseModel):
    """
    Represents a single constituent stock within an industry.
    """

    stock_code: str
    stock_name: str
    latest_price: float | None = None
    pct_change: float | None = None
    pe_ratio: float | None = None
    turnover_rate: float | None = None

    model_config = ConfigDict(from_attributes=True)
