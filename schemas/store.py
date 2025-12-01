from pydantic import BaseModel, AnyHttpUrl
from typing import Optional


class StoreCreate(BaseModel):
    name: str
    domain: str
    logo_url: Optional[AnyHttpUrl] = None


class StoreOut(BaseModel):
    id: int
    name: str
    domain: str
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True
