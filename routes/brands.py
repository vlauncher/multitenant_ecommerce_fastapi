from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.tenancy import get_current_store
from models.store import Store
from models.brand import Brand
from schemas.brand import BrandCreate, BrandUpdate, BrandOut

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("/", response_model=List[BrandOut])
def list_brands(store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    return db.query(Brand).filter(Brand.store_id == store.id).all()


@router.post("/", response_model=BrandOut, status_code=201)
def create_brand(data: BrandCreate, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    brand = Brand(store_id=store.id, name=data.name)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: int, data: BrandUpdate, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.store_id == store.id, Brand.id == brand_id).one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if data.name is not None:
        brand.name = data.name
    db.commit()
    db.refresh(brand)
    return brand


@router.delete("/{brand_id}", status_code=204)
def delete_brand(brand_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.store_id == store.id, Brand.id == brand_id).one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    db.delete(brand)
    db.commit()
    return None
