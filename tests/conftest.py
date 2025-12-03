import os
import types
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from core.db import Base, get_db
from core import config as core_config
from services import email as email_service
from models.user import User, user_store_roles
from models.store import Store
from security.password import hash_password
from security import jwt as jwt_utils


@pytest.fixture(scope="session", autouse=True)
def test_settings():
    # Speed up for tests
    core_config.settings.OTP_TTL_SECONDS = 600
    core_config.settings.OTP_RESEND_INTERVAL_SECONDS = 0
    core_config.settings.JWT_SECRET = "test-secret"
    core_config.settings.REFRESH_SECRET = "test-refresh"
    core_config.settings.DEBUG = True
    core_config.settings.TESTING = True
    yield


@pytest.fixture()
def db_session_override():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    def _get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    try:
        yield db
    finally:
        db.close()
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_email_send(monkeypatch):
    sent = []

    def _fake_send(to_email: str, subject: str, body: str) -> None:
        sent.append({"to": to_email, "subject": subject, "body": body})

    monkeypatch.setattr(email_service, "send_email", _fake_send)
    return sent


@pytest.fixture()
def client(db_session_override):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=None,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    yield db_session
    db_session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_store(db_session_override):
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
    db_session_override.add(store)
    db_session_override.commit()
    db_session_override.refresh(store)
    return store


@pytest.fixture
def test_user(db_session_override):
    """Create a test user."""
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        is_verified=True,
        is_superadmin=False,
    )
    db_session_override.add(user)
    db_session_override.commit()
    db_session_override.refresh(user)
    return user


@pytest.fixture
def test_user_with_store(db_session_override, test_user, test_store):
    """Create a test user with owner role in a store."""
    # Add user to store with owner role
    stmt = user_store_roles.insert().values(
        user_id=test_user.id,
        store_id=test_store.id,
        role="owner"
    )
    db_session_override.execute(stmt)
    db_session_override.commit()
    return test_user, test_store


@pytest.fixture
def auth_token(test_user):
    """Generate a valid JWT token for test user."""
    return jwt_utils.create_access_token(str(test_user.id))


@pytest.fixture
def auth_headers(auth_token):
    """Return authorization headers with valid token."""
    return {"Authorization": f"Bearer {auth_token}"}
