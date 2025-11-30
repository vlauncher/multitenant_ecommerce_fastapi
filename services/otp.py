from datetime import datetime, timedelta
import random
import json
import redis
from sqlalchemy.orm import Session

from core.config import settings
from models.user import User
from services.email import send_templated_email

# Redis connection for OTP storage
class _FakeRedis:
    def __init__(self):
        self._store = {}
        self._exp = {}

    def _cleanup(self, key):
        exp = self._exp.get(key)
        if exp is not None and datetime.utcnow().timestamp() > exp:
            self._store.pop(key, None)
            self._exp.pop(key, None)

    def setex(self, key, ttl, value):
        self._store[key] = value
        self._exp[key] = datetime.utcnow().timestamp() + int(ttl)

    def get(self, key):
        self._cleanup(key)
        return self._store.get(key)

    def exists(self, key):
        self._cleanup(key)
        return 1 if key in self._store else 0

    def ttl(self, key):
        self._cleanup(key)
        if key not in self._store:
            return -2  # key does not exist
        remain = int(self._exp.get(key, 0) - datetime.utcnow().timestamp())
        return max(remain, 0)

    def delete(self, key):
        self._store.pop(key, None)
        self._exp.pop(key, None)


redis_client = _FakeRedis() if settings.TESTING else redis.from_url(settings.REDIS_URL, decode_responses=True)

OTP_PREFIX = "otp:"
OTP_CODE_PREFIX = "otp_code:"
OTP_LAST_SENT_PREFIX = "otp:last:"
OTP_EXPIRY = settings.OTP_TTL_SECONDS


def _generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_verification_code(db: Session, user: User) -> str:
    """Generate and store OTP in Redis, send via email"""
    # Rate limiting using a simple Redis key with TTL (skip when interval set to 0)
    last_key = f"{OTP_LAST_SENT_PREFIX}{user.email}"
    if settings.OTP_RESEND_INTERVAL_SECONDS > 0 and redis_client.exists(last_key):
        ttl = redis_client.ttl(last_key)
        if ttl is None or ttl > 0:
            raise ValueError(f"Please wait {ttl if ttl and ttl > 0 else settings.OTP_RESEND_INTERVAL_SECONDS} seconds before requesting a new code")

    code = _generate_code()
    now = datetime.utcnow().isoformat()
    
    # Store OTP in Redis with TTL
    otp_key = f"{OTP_PREFIX}{user.email}"
    otp_data = {
        "code": code,
        "user_id": user.id,
        "email": user.email,
        "created_at": now,
        "attempts": 0
    }
    
    # Store with expiry
    redis_client.setex(
        otp_key, 
        OTP_EXPIRY, 
        json.dumps(otp_data)
    )
    # Also store code->email mapping to allow email-less verification
    code_key = f"{OTP_CODE_PREFIX}{code}"
    redis_client.setex(code_key, OTP_EXPIRY, user.email)

    # Set resend limiter key only if interval > 0
    if settings.OTP_RESEND_INTERVAL_SECONDS > 0:
        redis_client.setex(last_key, settings.OTP_RESEND_INTERVAL_SECONDS, "1")
    
    # Use templated email (plain text) - keep same body format for tests
    body_context = {"code": code, "first_name": getattr(user, "first_name", "")}
    send_templated_email(
        user.email,
        "Your verification code",
        "emails/verification_code.txt",
        body_context,
    )
    return code


def verify_code(db: Session, user: User, code: str) -> bool:
    """Verify OTP from Redis - no database query needed for OTP"""
    otp_key = f"{OTP_PREFIX}{user.email}"
    
    # Get OTP data from Redis
    otp_data_str = redis_client.get(otp_key)
    if not otp_data_str:
        return False
    
    try:
        otp_data = json.loads(otp_data_str)
        
        # Check if max attempts exceeded (5 attempts)
        if otp_data.get("attempts", 0) >= 5:
            redis_client.delete(otp_key)
            return False
        
        # Verify code
        if otp_data["code"] != code:
            # Increment attempts
            otp_data["attempts"] += 1
            redis_client.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            return False
        
        # Success - delete OTP from Redis
        redis_client.delete(otp_key)
        # Remove reverse mapping as well
        redis_client.delete(f"{OTP_CODE_PREFIX}{code}")
        return True
        
    except (json.JSONDecodeError, KeyError):
        # Corrupted data - delete and fail
        redis_client.delete(otp_key)
        return False


def verify_code_without_email(code: str) -> tuple[bool, str | None]:
    """Verify OTP using only the code. Returns (ok, email)."""
    code_key = f"{OTP_CODE_PREFIX}{code}"
    email = redis_client.get(code_key)
    if not email:
        return False, None
    # Delegate to email-based verification for attempt counting and cleanup
    otp_key = f"{OTP_PREFIX}{email}"
    otp_data_str = redis_client.get(otp_key)
    if not otp_data_str:
        return False, None
    try:
        otp_data = json.loads(otp_data_str)
        if otp_data.get("attempts", 0) >= 5:
            redis_client.delete(otp_key)
            redis_client.delete(code_key)
            return False, None
        if otp_data.get("code") != code:
            otp_data["attempts"] = otp_data.get("attempts", 0) + 1
            redis_client.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            return False, None
        # Success
        redis_client.delete(otp_key)
        redis_client.delete(code_key)
        return True, email
    except (json.JSONDecodeError, KeyError):
        redis_client.delete(otp_key)
        redis_client.delete(code_key)
        return False, None


def get_otp_status(email: str) -> dict:
    """Get OTP status for debugging/monitoring"""
    otp_key = f"{OTP_PREFIX}{email}"
    otp_data_str = redis_client.get(otp_key)
    
    if not otp_data_str:
        return {"exists": False}
    
    try:
        otp_data = json.loads(otp_data_str)
        ttl = redis_client.ttl(otp_key)
        return {
            "exists": True,
            "email": otp_data["email"],
            "created_at": otp_data["created_at"],
            "attempts": otp_data.get("attempts", 0),
            "ttl_seconds": ttl
        }
    except (json.JSONDecodeError, KeyError):
        redis_client.delete(otp_key)
        return {"exists": False}
