from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from core.db import get_db, Base, engine
from models.user import User
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenPair,
    VerifyOtpRequest,
    ResendOtpRequest,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ResetPasswordConfirm,
    RefreshTokenRequest,
)
from schemas.users import UserOut
from security.password import hash_password, verify_password
from security import jwt as jwt_utils
from services.otp import send_verification_code, verify_code, verify_code_without_email
from services.email import send_templated_email

router = APIRouter(prefix="/auth", tags=["auth"])


# Ensure tables for this minimal app (in lieu of migrations)
Base.metadata.create_all(bind=engine)


def get_current_user(
    db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None, alias="Authorization")
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt_utils.decode_access(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email.lower()).one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    send_verification_code(db, user)
    return user


@router.post("/login", response_model=TokenPair)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified")
    access = jwt_utils.create_access_token(str(user.id))
    refresh = jwt_utils.create_refresh_token(str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/verify-otp")
def verify_otp(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    # Verify using only the code via Redis mapping
    ok, email = verify_code_without_email(data.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    # Lookup user by email obtained from Redis
    user = db.query(User).filter(User.email == email.lower()).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Mark user as verified
    user.is_verified = True
    db.commit()
    # Send confirmation email (templated)
    send_templated_email(
        user.email,
        "Email verified",
        "emails/verification_success.txt",
        {"first_name": getattr(user, "first_name", "")},
    )
    return {"detail": "Verified"}


@router.post("/resend-otp")
def resend_otp(data: ResendOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        send_verification_code(db, user)
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"detail": "OTP sent"}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"detail": "Password changed"}


@router.post("/reset-password/request")
def reset_password_request(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).one_or_none()
    if user:
        send_verification_code(db, user)
    return {"detail": "If the email exists, a code has been sent"}


@router.post("/reset-password/confirm")
def reset_password_confirm(data: ResetPasswordConfirm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ok = verify_code(db, user, data.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    # Send password reset confirmation email
    send_templated_email(
        user.email,
        "Password reset successful",
        "emails/password_reset_success.txt",
        {"first_name": getattr(user, "first_name", "")},
    )
    return {"detail": "Password reset"}


@router.post("/refresh-token", response_model=TokenPair)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt_utils.decode_refresh(data.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    access = jwt_utils.create_access_token(str(user.id))
    refresh = jwt_utils.create_refresh_token(str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh)


@router.get("/otp-status/{email}")
def get_otp_status(email: str):
    """Get OTP status for debugging (development only)"""
    from services.otp import get_otp_status
    return get_otp_status(email.lower())
