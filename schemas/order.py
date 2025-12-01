from pydantic import BaseModel, EmailStr
from typing import List, Optional


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    email: EmailStr
    currency: str = "NGN"
    items: List[OrderItemIn]


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    total: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    email: EmailStr
    currency: str
    status: str
    subtotal: float
    total: float
    items: List[OrderItemOut]

    class Config:
        from_attributes = True
