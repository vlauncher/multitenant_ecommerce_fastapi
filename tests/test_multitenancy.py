"""
Tests for multitenancy features.
"""
import pytest
from fastapi import status
from models.store import Store
from models.user import User, user_store_roles


class TestStoreResolution:
    """Test store resolution from domain/subdomain."""
    
    def test_get_store_by_domain(self, client, test_store):
        """Test store resolution by domain header."""
        response = client.get(
            "/products/",
            headers={"X-Store-Domain": test_store.domain}
        )
        # Should not return 404 for store not found
        assert response.status_code != status.HTTP_404_NOT_FOUND
    
    def test_store_not_found(self, client):
        """Test 404 when store domain doesn't exist."""
        response = client.get(
            "/products/",
            headers={"X-Store-Domain": "nonexistent.example.com"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Store not found" in response.json()["detail"]
    
    def test_inactive_store_forbidden(self, client, db, test_store):
        """Test accessing inactive store returns 403."""
        test_store.is_active = False
        db.commit()
        
        response = client.get(
            "/products/",
            headers={"X-Store-Domain": test_store.domain}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "inactive" in response.json()["detail"]
    
    def test_suspended_store_forbidden(self, client, db, test_store):
        """Test accessing suspended store returns 403."""
        test_store.is_suspended = True
        test_store.suspension_reason = "Payment overdue"
        db.commit()
        
        response = client.get(
            "/products/",
            headers={"X-Store-Domain": test_store.domain}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "suspended" in response.json()["detail"]


class TestUserStoreRoles:
    """Test user roles in stores."""
    
    def test_user_owner_role(self, db, test_user, test_store):
        """Test user with owner role."""
        stmt = user_store_roles.insert().values(
            user_id=test_user.id,
            store_id=test_store.id,
            role="owner"
        )
        db.execute(stmt)
        db.commit()
        
        # Verify role was assigned
        result = db.query(user_store_roles.c.role).filter(
            user_store_roles.c.user_id == test_user.id,
            user_store_roles.c.store_id == test_store.id
        ).first()
        assert result[0] == "owner"
    
    def test_user_multiple_stores(self, db, test_user):
        """Test user can have roles in multiple stores."""
        store1 = Store(
            name="Store 1",
            domain="store1.example.com",
            is_active=True,
        )
        store2 = Store(
            name="Store 2",
            domain="store2.example.com",
            is_active=True,
        )
        db.add_all([store1, store2])
        db.commit()
        
        # Add user to both stores with different roles
        db.execute(user_store_roles.insert().values(
            user_id=test_user.id,
            store_id=store1.id,
            role="owner"
        ))
        db.execute(user_store_roles.insert().values(
            user_id=test_user.id,
            store_id=store2.id,
            role="staff"
        ))
        db.commit()
        
        # Verify both roles exist
        roles = db.query(user_store_roles.c.role).filter(
            user_store_roles.c.user_id == test_user.id
        ).all()
        assert len(roles) == 2
        assert "owner" in [r[0] for r in roles]
        assert "staff" in [r[0] for r in roles]


class TestStorePlans:
    """Test store subscription plans and limits."""
    
    def test_free_plan_defaults(self, db):
        """Test free plan has appropriate defaults."""
        store = Store(
            name="Free Store",
            domain="free.example.com",
            plan="free",
            is_active=True,
        )
        db.add(store)
        db.commit()
        
        assert store.plan == "free"
        assert store.max_products is None or store.max_products > 0
    
    def test_premium_plan_limits(self, db):
        """Test premium plan has higher limits."""
        store = Store(
            name="Premium Store",
            domain="premium.example.com",
            plan="premium",
            max_products=1000,
            max_orders_per_month=10000,
            max_storage_mb=5000,
            is_active=True,
        )
        db.add(store)
        db.commit()
        
        assert store.plan == "premium"
        assert store.max_products == 1000
        assert store.max_orders_per_month == 10000
        assert store.max_storage_mb == 5000


class TestStoreSettings:
    """Test store configuration and settings."""
    
    def test_store_theme_config(self, db):
        """Test store can have theme configuration."""
        theme = {
            "primary_color": "#FF5733",
            "secondary_color": "#33FF57",
            "font_family": "Arial",
        }
        store = Store(
            name="Themed Store",
            domain="themed.example.com",
            theme_config=theme,
            is_active=True,
        )
        db.add(store)
        db.commit()
        db.refresh(store)
        
        assert store.theme_config == theme
        assert store.theme_config["primary_color"] == "#FF5733"
    
    def test_store_custom_settings(self, db):
        """Test store can have custom settings."""
        settings = {
            "enable_reviews": True,
            "enable_wishlist": True,
            "currency": "USD",
            "tax_rate": 0.1,
        }
        store = Store(
            name="Custom Store",
            domain="custom.example.com",
            settings=settings,
            is_active=True,
        )
        db.add(store)
        db.commit()
        db.refresh(store)
        
        assert store.settings == settings
        assert store.settings["enable_reviews"] is True
