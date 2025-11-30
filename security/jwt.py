from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from core.config import settings


def _encode(payload: Dict[str, Any], secret: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=minutes)
    to_encode = {"iat": int(now.timestamp()), "exp": int(exp.timestamp()), **payload}
    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALG)


def create_access_token(sub: str, extra: Dict[str, Any] | None = None) -> str:
    payload = {"sub": sub, "type": "access"}
    if extra:
        payload.update(extra)
    return _encode(payload, settings.JWT_SECRET, settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def create_refresh_token(sub: str, extra: Dict[str, Any] | None = None) -> str:
    payload = {"sub": sub, "type": "refresh"}
    if extra:
        payload.update(extra)
    return _encode(payload, settings.REFRESH_SECRET, settings.REFRESH_TOKEN_EXPIRE_MINUTES)


def decode_access(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])


def decode_refresh(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.REFRESH_SECRET, algorithms=[settings.JWT_ALG])
