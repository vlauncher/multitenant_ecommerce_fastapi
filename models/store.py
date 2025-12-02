from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subdomain: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Tenant owner/admin
    owner_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    
    # Subscription & limits
    plan: Mapped[str] = mapped_column(String(50), default="free")  # free, basic, premium, enterprise
    max_products: Mapped[int | None] = mapped_column(nullable=True)
    max_orders_per_month: Mapped[int | None] = mapped_column(nullable=True)
    max_storage_mb: Mapped[int | None] = mapped_column(nullable=True)
    
    # Tenant settings
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    theme_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Contact & business info
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subscription_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
