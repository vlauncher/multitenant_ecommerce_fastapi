from typing import List, Dict

from fastapi import status

from core import config as core_config


def _extract_last_code(sent: List[Dict]) -> str:
    assert sent, "No email sent"
    body = sent[-1]["body"]
    # Body format: "Your OTP code is: 123456"
    return body.strip().split()[-1]


def test_register_then_verify_and_login(client, mock_email_send):
    # Register
    r = client.post(
        "/auth/register",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
        },
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text
    assert r.json()["email"] == "john@example.com"

    # Cannot login before verification
    r = client.post(
        "/auth/login",
        json={"email": "john@example.com", "password": "Password123!"},
    )
    assert r.status_code == status.HTTP_403_FORBIDDEN

    # Verify using OTP from mocked email
    code = _extract_last_code(mock_email_send)
    r = client.post(
        "/auth/verify-otp",
        json={"code": code},
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    # Login now works
    r = client.post(
        "/auth/login",
        json={"email": "john@example.com", "password": "Password123!"},
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    tokens = r.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    # Change password with wrong old password
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post(
        "/auth/change-password",
        json={"old_password": "WrongPass1!", "new_password": "NewPassword123!"},
        headers=headers,
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST

    # Change password success
    r = client.post(
        "/auth/change-password",
        json={"old_password": "Password123!", "new_password": "NewPassword123!"},
        headers=headers,
    )
    assert r.status_code == status.HTTP_200_OK

    # Login with new password works
    r = client.post(
        "/auth/login",
        json={"email": "john@example.com", "password": "NewPassword123!"},
    )
    assert r.status_code == status.HTTP_200_OK


def test_resend_otp_rate_limit(client, mock_email_send, monkeypatch):
    # Set resend interval to 2 seconds to test rate limiting
    monkeypatch.setattr(core_config.settings, "OTP_RESEND_INTERVAL_SECONDS", 2, raising=False)

    client.post(
        "/auth/register",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "password": "Password123!",
        },
    )

    # First resend should fail due to rate limit (immediate)
    r = client.post(
        "/auth/resend-otp",
        json={"email": "jane@example.com"},
    )
    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # Remove rate limit and try again
    monkeypatch.setattr(core_config.settings, "OTP_RESEND_INTERVAL_SECONDS", 0, raising=False)
    r = client.post(
        "/auth/resend-otp",
        json={"email": "jane@example.com"},
    )
    assert r.status_code == status.HTTP_200_OK


def test_reset_password_flow(client, mock_email_send):
    # Register new user
    client.post(
        "/auth/register",
        json={
            "first_name": "Rick",
            "last_name": "Sanchez",
            "email": "rick@example.com",
            "password": "PortalGun123!",
        },
    )

    # Request reset returns generic message
    r = client.post("/auth/reset-password/request", json={"email": "rick@example.com"})
    assert r.status_code == status.HTTP_200_OK

    # Use last code to reset password - get the reset OTP code (2nd email)
    reset_code = _extract_last_code(mock_email_send)
    r = client.post(
        "/auth/reset-password/confirm",
        json={
            "email": "rick@example.com",
            "code": reset_code,
            "new_password": "NewPortalGun123!",
        },
    )
    assert r.status_code == status.HTTP_200_OK

    # Still not verified; attempt login should be forbidden
    r = client.post(
        "/auth/login",
        json={"email": "rick@example.com", "password": "NewPortalGun123!"},
    )
    assert r.status_code == status.HTTP_403_FORBIDDEN

    # Request a new OTP for verification
    r = client.post("/auth/resend-otp", json={"email": "rick@example.com"})
    assert r.status_code == status.HTTP_200_OK

    # Use the new OTP code for verification
    new_otp_code = _extract_last_code(mock_email_send)
    r = client.post(
        "/auth/verify-otp",
        json={"code": new_otp_code},
    )
    assert r.status_code == status.HTTP_200_OK

    r = client.post(
        "/auth/login",
        json={"email": "rick@example.com", "password": "NewPortalGun123!"},
    )
    assert r.status_code == status.HTTP_200_OK


def test_refresh_token(client, mock_email_send):
    # Register fresh user
    r = client.post(
        "/auth/register",
        json={
            "first_name": "Morty",
            "last_name": "Smith",
            "email": "morty@example.com",
            "password": "OhJeez123!",
        },
    )
    assert r.status_code == status.HTTP_201_CREATED

    # Verify
    code = _extract_last_code(mock_email_send)
    r = client.post(
        "/auth/verify-otp",
        json={"code": code},
    )
    assert r.status_code == status.HTTP_200_OK

    # Login to obtain refresh
    r = client.post(
        "/auth/login",
        json={"email": "morty@example.com", "password": "OhJeez123!"},
    )
    assert r.status_code == status.HTTP_200_OK
    refresh = r.json()["refresh_token"]

    # Refresh
    r = client.post("/auth/refresh-token", json={"refresh_token": refresh})
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert "access_token" in data and "refresh_token" in data


def test_protected_requires_auth(client):
    r = client.post(
        "/auth/change-password",
        json={"old_password": "x", "new_password": "y"},
    )
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
