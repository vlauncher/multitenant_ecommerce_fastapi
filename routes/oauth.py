from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from core.config import settings
from core.db import get_db
from models.user import User
from security.password import hash_password
from security import jwt as jwt_utils
from schemas.auth import TokenPair

router = APIRouter(prefix="/auth/google", tags=["oauth"]) 

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login")
async def google_login(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", response_model=TokenPair)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    token = await oauth.google.authorize_access_token(request)
    # Try to parse id_token for user info
    userinfo = None
    try:
        userinfo = await oauth.google.parse_id_token(request, token)
    except Exception:
        pass
    if not userinfo:
        # Fallback to userinfo endpoint
        resp = await oauth.google.get("userinfo")
        userinfo = resp.json()
    email = (userinfo.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")
    first = userinfo.get("given_name") or ""
    last = userinfo.get("family_name") or ""

    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        user = User(
            first_name=first or "Google",
            last_name=last or "User",
            email=email,
            password_hash=hash_password(email + "|google"),
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.is_verified:
            user.is_verified = True
            db.commit()

    access = jwt_utils.create_access_token(str(user.id))
    refresh = jwt_utils.create_refresh_token(str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh)
