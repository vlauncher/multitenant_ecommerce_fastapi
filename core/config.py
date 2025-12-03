import os
from typing import Optional

from dotenv import load_dotenv

# Load .env file
load_dotenv('.env')


def get_env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


class Settings:
    def __init__(self):
        self.APP_NAME: str = get_env("APP_NAME", "FastAPI Microservice")
        self.APP_VERSION: str = get_env("APP_VERSION", "1.0.0")

        # App settings - need to be defined first for database switching
        self.DEBUG: bool = get_env("DEBUG", "False").lower() == "true"
        self.TESTING: bool = get_env("TESTING", "False").lower() == "true"
        
        # Database configuration - switch based on environment
        if self.TESTING:
            # In-memory SQLite for testing
            self.DATABASE_URL: str = "sqlite:///:memory:"
            self.SQLALCHEMY_ECHO: bool = False
        elif self.DEBUG:
            # File-based SQLite for development
            self.DATABASE_URL: str = get_env("DATABASE_URL", "sqlite:///./db.sqlite3")
            self.SQLALCHEMY_ECHO: bool = True
        else:
            # PostgreSQL for production
            self.DATABASE_URL: str = get_env("POSTGRES_DATABASE_URL", "postgresql://user:password@localhost/dbname")
            self.SQLALCHEMY_ECHO: bool = False

        self.JWT_SECRET: str = get_env("JWT_SECRET", "dev-secret-change")
        self.JWT_ALG: str = get_env("JWT_ALG", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(get_env("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

        self.REFRESH_SECRET: str = get_env("REFRESH_SECRET", "dev-refresh-change")
        self.REFRESH_TOKEN_EXPIRE_MINUTES: int = int(get_env("REFRESH_TOKEN_EXPIRE_MINUTES", "60*24*7")) if "*" in get_env("REFRESH_TOKEN_EXPIRE_MINUTES", "10080") else int(get_env("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))

        self.SMTP_HOST: str = get_env("SMTP_HOST", "smtp.gmail.com")
        self.SMTP_PORT: int = int(get_env("SMTP_PORT", "587"))
        self.SMTP_USERNAME: str = get_env("SMTP_USERNAME", "")
        self.SMTP_PASSWORD: str = get_env("SMTP_PASSWORD", "")
        self.SMTP_FROM: str = get_env("SMTP_FROM", "no-reply@example.com")

        self.OTP_TTL_SECONDS: int = int(get_env("OTP_TTL_SECONDS", "600"))
        self.OTP_RESEND_INTERVAL_SECONDS: int = int(get_env("OTP_RESEND_INTERVAL_SECONDS", "60"))
        
        # Redis/Celery settings
        self.REDIS_URL: str = get_env("REDIS_URL", "redis://localhost:6379/0")

        # Paystack settings
        self.PAYSTACK_SECRET_KEY: str = get_env("PAYSTACK_SECRET_KEY", "")
        self.PAYSTACK_CALLBACK_URL: str = get_env("PAYSTACK_CALLBACK_URL", "")

        # Google OAuth settings
        self.GOOGLE_CLIENT_ID: str = get_env("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET: str = get_env("GOOGLE_CLIENT_SECRET", "")
        self.GOOGLE_REDIRECT_URI: str = get_env("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")


settings = Settings()
