"""
Pytest configuration and fixtures for testing.
Uses in-memory SQLite database for fast, isolated tests.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set testing environment before importing app
os.environ["TESTING"] = "True"
os.environ["DEBUG"] = "False"

from core.db import Base, get_db
from main import app
from models.user import User, user_store_roles
from models.store import Store
from security.password import hash_password
from security import jwt as jwt_utils


# Create in-memory SQLite engine for testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override get_db dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    yield db_session
    db_session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    """Create a test client with overridden database dependency."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        is_verified=True,
        is_superadmin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_store(db):
    """Create a test store."""
    store = Store(
        name="Test Store",
        domain="test.example.com",
        subdomain="test",
        owner_id=None,
        plan="free",
        is_active=True,
        is_suspended=False,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@pytest.fixture
def test_user_with_store(db, test_user, test_store):
    """Create a test user with owner role in a store."""
    # Add user to store with owner role
    stmt = user_store_roles.insert().values(
        user_id=test_user.id,
        store_id=test_store.id,
        role="owner"
    )
    db.execute(stmt)
    db.commit()
    return test_user, test_store


@pytest.fixture
def auth_token(test_user):
    """Generate a valid JWT token for test user."""
    return jwt_utils.create_access_token(str(test_user.id))


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers with valid token."""
    return {"Authorization": f"Bearer {auth_token}"}
