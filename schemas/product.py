from pydantic import BaseModel
from typing import Optional


class ProductCreate(BaseModel):
    name: str
    slug: str
    price: float
    currency: str = "NGN"
    stock: int = 0
    brand_id: Optional[int] = None
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    stock: Optional[int] = None
    brand_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    price: float
    currency: str
    stock: int
    brand_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
