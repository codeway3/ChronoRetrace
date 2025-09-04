from datetime import date
from typing import List

from pydantic import BaseModel, ConfigDict


class CorporateActionBase(BaseModel):
    symbol: str
    action_type: str
    ex_date: date
    value: float


class CorporateActionCreate(CorporateActionBase):
    pass


class CorporateActionInDB(CorporateActionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CorporateActionResponse(BaseModel):
    symbol: str
    actions: List[CorporateActionInDB]
