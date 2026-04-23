from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    # SQLite-friendly storage
    days_of_week: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    notify_time: Mapped[str] = mapped_column(String(8), nullable=False)  # HH:MM
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
