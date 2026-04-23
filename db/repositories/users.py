from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


class UsersRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        res = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return res.scalar_one_or_none()

    async def upsert_profile(
        self,
        *,
        telegram_id: int,
        name: str | None,
        goal: str,
        level: str,
        frequency: int,
        preferred_time: str,
        location: str,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id)
            self.session.add(user)

        user.name = name
        user.goal = goal
        user.level = level
        user.frequency = frequency
        user.preferred_time = preferred_time
        user.location = location
        await self.session.flush()
        return user

    async def set_water_norm(self, *, telegram_id: int, norm_ml: int) -> None:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
        user.water_norm_ml = norm_ml
        await self.session.flush()

    async def set_reminders_enabled(self, *, telegram_id: int, enabled: bool) -> None:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
        user.reminders_enabled = enabled
        await self.session.flush()

