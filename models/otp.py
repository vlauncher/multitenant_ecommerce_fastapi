from datetime import datetime, timedelta

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base


class OTP(Base):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(6), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime)
    send_count: Mapped[int] = mapped_column(Integer, default=1)

    user = relationship("User")

    @staticmethod
    def expiry(ttl_seconds: int) -> datetime:
        return datetime.utcnow() + timedelta(seconds=ttl_seconds)
