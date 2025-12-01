from pydantic import BaseModel
from typing import Optional


class BrandCreate(BaseModel):
    name: str


class BrandUpdate(BaseModel):
    name: Optional[str] = None


class BrandOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
