from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from core.db import get_db
from core.tenancy import get_current_store
from models.store import Store
from schemas.store import StoreCreate, StoreOut

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/current", response_model=StoreOut)
def get_store(request: Request, store: Store = Depends(get_current_store)):
    return store


@router.post("/", response_model=StoreOut, status_code=201)
def create_store(data: StoreCreate, db: Session = Depends(get_db)):
    existing = db.query(Store).filter(Store.domain == data.domain.lower()).one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")
    store = Store(name=data.name.strip(), domain=data.domain.lower(), logo_url=data.logo_url)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store
