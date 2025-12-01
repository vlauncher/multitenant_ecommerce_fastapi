from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.tenancy import get_current_store
from models.store import Store
from models.order import Order
from models.payment import Payment
from schemas.payment import (
    PaymentInitRequest,
    PaymentInitResponse,
    PaymentVerifyRequest,
    PaymentOut,
)
from services.paystack import initialize_transaction, verify_transaction

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/init", response_model=PaymentInitResponse)
def init_payment(data: PaymentInitRequest, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.store_id == store.id, Order.id == data.order_id).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.total is None or float(order.total) <= 0:
        raise HTTPException(status_code=400, detail="Order total must be greater than 0")

    # Initialize transaction with Paystack
    resp = initialize_transaction(
        email=order.email,
        amount=float(order.total),
        callback_url=data.callback_url,
        metadata={"order_id": order.id, "store_id": store.id},
    )
    if not resp.get("status"):
        raise HTTPException(status_code=400, detail=resp.get("message", "Unable to initialize payment"))

    d = resp.get("data", {})
    reference = d.get("reference")
    if not reference:
        raise HTTPException(status_code=400, detail="Missing reference from provider")

    payment = Payment(
        store_id=store.id,
        order_id=order.id,
        provider="paystack",
        reference=reference,
        amount=order.total,
        currency=order.currency,
        status="initialized",
        raw_response=resp,
    )
    db.add(payment)
    db.commit()
    return {
        "authorization_url": d.get("authorization_url"),
        "access_code": d.get("access_code"),
        "reference": reference,
    }


@router.post("/verify", response_model=PaymentOut)
def verify_payment(data: PaymentVerifyRequest, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.store_id == store.id, Payment.reference == data.reference).one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    resp = verify_transaction(data.reference)
    payment.raw_response = resp
    if resp.get("status") and resp.get("data", {}).get("status") == "success":
        payment.status = "success"
        # Mark order paid
        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if order:
            order.status = "paid"
    else:
        payment.status = resp.get("data", {}).get("status") or "failed"
    db.commit()
    db.refresh(payment)
    return payment
