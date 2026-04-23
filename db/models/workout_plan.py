from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
