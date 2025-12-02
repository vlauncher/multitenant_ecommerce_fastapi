from typing import Optional
from datetime import datetime
from fastapi import Header, HTTPException, status, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.db import get_db
from models.store import Store
from models.user import User, user_store_roles


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
    
    # Try exact domain match first
    store = db.query(Store).filter(Store.domain == domain).one_or_none()
    
    # If not found, try subdomain match (e.g., mystore.platform.com)
    if not store and "." in domain:
        subdomain = domain.split(".")[0]
        store = db.query(Store).filter(Store.subdomain == subdomain).one_or_none()
    
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    
    # Check if store is active
    if not store.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store is inactive")
    
    # Check if store is suspended
    if store.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Store is suspended: {store.suspension_reason or 'Contact support'}"
        )
    
    # Check subscription status
    if store.subscription_ends_at and store.subscription_ends_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Store subscription has expired"
        )
    
    return store


def get_user_role_in_store(user_id: int, store_id: int, db: Session) -> Optional[str]:
    """Get user's role in a specific store."""
    result = db.query(user_store_roles.c.role).filter(
        user_store_roles.c.user_id == user_id,
        user_store_roles.c.store_id == store_id
    ).first()
    return result[0] if result else None


def check_store_access(user: User, store: Store, db: Session, required_role: Optional[str] = None) -> bool:
    """Check if user has access to store with optional role requirement."""
    if user.is_superadmin:
        return True
    
    role = get_user_role_in_store(user.id, store.id, db)
    if not role:
        return False
    
    if required_role:
        role_hierarchy = {"owner": 4, "admin": 3, "staff": 2, "member": 1}
        user_level = role_hierarchy.get(role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        return user_level >= required_level
    
    return True


def require_store_role(required_role: str = "member"):
    """Dependency to require specific role in current store."""
    def _check_role(
        store: Store = Depends(get_current_store),
        user: User = Depends(get_current_user),  # You'll need to implement this
        db: Session = Depends(get_db)
    ):
        if not check_store_access(user, store, db, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher"
            )
        return store
    return _check_role


def get_store_usage_stats(store_id: int, db: Session) -> dict:
    """Get current usage statistics for a store."""
    from models.product import Product
    from models.order import Order
    
    product_count = db.query(func.count(Product.id)).filter(Product.store_id == store_id).scalar()
    
    # Orders this month
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    orders_this_month = db.query(func.count(Order.id)).filter(
        Order.store_id == store_id,
        Order.created_at >= month_start
    ).scalar()
    
    return {
        "product_count": product_count,
        "orders_this_month": orders_this_month,
    }


def check_store_limits(store: Store, db: Session, check_type: str = "products") -> bool:
    """Check if store has reached its limits."""
    stats = get_store_usage_stats(store.id, db)
    
    if check_type == "products" and store.max_products:
        return stats["product_count"] < store.max_products
    
    if check_type == "orders" and store.max_orders_per_month:
        return stats["orders_this_month"] < store.max_orders_per_month
    
    return True


# Placeholder for get_current_user - you'll need to implement this based on your auth
def get_current_user():
    """Placeholder - implement based on your JWT auth logic."""
    pass
