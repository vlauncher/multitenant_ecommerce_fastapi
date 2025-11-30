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
