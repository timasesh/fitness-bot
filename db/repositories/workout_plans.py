from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import WorkoutPlan


class WorkoutPlansRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_for_user(self, *, user_id: int) -> WorkoutPlan | None:
        q = (
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .order_by(desc(WorkoutPlan.created_at))
            .limit(1)
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

