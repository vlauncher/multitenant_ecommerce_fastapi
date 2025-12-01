from typing import Optional
from fastapi import Header, HTTPException, status, Request, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from models.store import Store


def resolve_domain(request: Request, x_store_domain: Optional[str] = Header(default=None, alias="X-Store-Domain")) -> str:
    """Resolve store domain from X-Store-Domain header or Host header."""
    if x_store_domain:
        return x_store_domain.lower()
    host = request.headers.get("host") or request.headers.get("Host")
    if not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing store domain")
    return host.split(":")[0].lower()


def get_current_store(request: Request, db: Session = Depends(get_db)) -> Store:
    """FastAPI dependency that returns the Store matching the current domain."""
    domain = resolve_domain(request)
    store = db.query(Store).filter(Store.domain == domain).one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store
