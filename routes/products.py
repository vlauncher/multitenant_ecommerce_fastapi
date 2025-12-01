from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from core.db import get_db
from core.tenancy import get_current_store
from models.store import Store
from models.product import Product
from models.brand import Brand
from schemas.product import ProductCreate, ProductUpdate, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductOut])
def list_products(store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    qs = db.query(Product).filter(Product.store_id == store.id)
    return qs.all()


@router.post("/", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    # Ensure slug not already used in this store
    existing = db.query(Product).filter(Product.store_id == store.id, Product.slug == data.slug).one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists in this store")

    if data.brand_id:
        brand = db.query(Brand).filter(Brand.id == data.brand_id, Brand.store_id == store.id).one_or_none()
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found for this store")

    product = Product(
        store_id=store.id,
        brand_id=data.brand_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        price=data.price,
        currency=data.currency,
        stock=data.stock,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{slug}", response_model=ProductOut)
def get_product(slug: str, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.store_id == store.id, Product.slug == slug).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.store_id == store.id, Product.id == product_id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.brand_id is not None:
        if data.brand_id:
            brand = db.query(Brand).filter(Brand.id == data.brand_id, Brand.store_id == store.id).one_or_none()
            if not brand:
                raise HTTPException(status_code=404, detail="Brand not found for this store")
        product.brand_id = data.brand_id

    if data.name is not None:
        product.name = data.name
    if data.price is not None:
        product.price = data.price
    if data.currency is not None:
        product.currency = data.currency
    if data.stock is not None:
        product.stock = data.stock
    if data.description is not None:
        product.description = data.description
    if data.is_active is not None:
        product.is_active = data.is_active

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.store_id == store.id, Product.id == product_id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return None
