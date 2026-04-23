from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import WaterLog


class WaterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, *, user_id: int, amount_ml: int) -> None:
        self.session.add(WaterLog(user_id=user_id, amount_ml=amount_ml))
        await self.session.flush()

    async def total_for_date(self, *, user_id: int, date: dt.date) -> int:
        start = dt.datetime.combine(date, dt.time.min, tzinfo=dt.timezone.utc)
        end = dt.datetime.combine(date, dt.time.max, tzinfo=dt.timezone.utc)
        q = select(func.coalesce(func.sum(WaterLog.amount_ml), 0)).where(WaterLog.user_id == user_id)
        q = q.where(WaterLog.logged_at >= start).where(WaterLog.logged_at <= end)
        res = await self.session.execute(q)
        return int(res.scalar_one())

