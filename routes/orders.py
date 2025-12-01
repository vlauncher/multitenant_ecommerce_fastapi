from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from core.db import get_db
from core.tenancy import get_current_store
from models.store import Store
from models.order import Order
from models.order_item import OrderItem
from models.product import Product
from schemas.order import OrderCreate, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_decimal(value: float | int | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@router.get("/", response_model=List[OrderOut])
def list_orders(store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    return db.query(Order).filter(Order.store_id == store.id).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.store_id == store.id, Order.id == order_id).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=OrderOut, status_code=201)
def create_order(data: OrderCreate, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="Order must contain items")

    # Fetch all products in a single query
    product_ids = [item.product_id for item in data.items]
    products_map = {
        p.id: p for p in db.query(Product).filter(Product.store_id == store.id, Product.id.in_(product_ids)).all()
    }

    if len(products_map) != len(set(product_ids)):
        raise HTTPException(status_code=404, detail="One or more products not found for this store")

    order = Order(store_id=store.id, email=data.email, currency=data.currency, status="pending")
    db.add(order)
    db.flush()

    subtotal = Decimal("0.00")
    items: list[OrderItem] = []
    for item in data.items:
        product = products_map[item.product_id]
        unit_price = _to_decimal(product.price)
        total = unit_price * _to_decimal(item.quantity)
        subtotal += total
        items.append(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=unit_price,
                total=total,
            )
        )

    order.subtotal = subtotal
    order.total = subtotal  # taxes/discounts could be applied here
    db.add_all(items)
    db.commit()
    db.refresh(order)
    return order
