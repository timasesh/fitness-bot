from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Schedule


class SchedulesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_for_user(self, *, user_id: int) -> Schedule | None:
        res = await self.session.execute(select(Schedule).where(Schedule.user_id == user_id))
        return res.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id: int,
        days_of_week: list[int],
        notify_time: str,
        is_active: bool,
    ) -> Schedule:
        schedule = await self.get_for_user(user_id=user_id)
        if schedule is None:
            schedule = Schedule(user_id=user_id, days_of_week=days_of_week, notify_time=notify_time, is_active=is_active)
            self.session.add(schedule)
        else:
            schedule.days_of_week = days_of_week
            schedule.notify_time = notify_time
            schedule.is_active = is_active

        await self.session.flush()
        return schedule

