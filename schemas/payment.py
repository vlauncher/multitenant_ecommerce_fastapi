from pydantic import BaseModel
from typing import Optional


class PaymentInitRequest(BaseModel):
    order_id: int
    callback_url: Optional[str] = None


class PaymentInitResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str


class PaymentVerifyRequest(BaseModel):
    reference: str


class PaymentOut(BaseModel):
    id: int
    provider: str
    reference: str
    amount: float
    currency: str
    status: str

    class Config:
        from_attributes = True
