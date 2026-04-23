from __future__ import annotations

import datetime as dt

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiogram import Bot

from db.models import Schedule, User, WaterLog


_DOW_MAP = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}


class SchedulerService:
    def __init__(
        self,
        *,
        bot: Bot,
        sessionmaker: async_sessionmaker[AsyncSession],
    ) -> None:
        self.bot = bot
        self.sessionmaker = sessionmaker
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    async def start(self) -> None:
        await self._load_workout_schedules()
        self._schedule_water_reminder()
        self.scheduler.start()

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _load_workout_schedules(self) -> None:
        async with self.sessionmaker() as session:
            q = select(Schedule, User.telegram_id).join(User, User.id == Schedule.user_id).where(Schedule.is_active == True)  # noqa: E712
            res = await session.execute(q)
            rows = res.all()

        for schedule, telegram_id in rows:
            self._schedule_workout_job(
                telegram_id=telegram_id,
                schedule_id=schedule.id,
                days=schedule.days_of_week,
                time_hhmm=schedule.notify_time,
            )

    def _schedule_workout_job(self, *, telegram_id: int, schedule_id: int, days: list[int], time_hhmm: str) -> None:
        try:
            hour = int(time_hhmm.split(":")[0])
            minute = int(time_hhmm.split(":")[1])
        except Exception:
            return

        dow = ",".join(_DOW_MAP[d] for d in sorted(set(days)) if d in _DOW_MAP)
        if not dow:
            return

        self.scheduler.add_job(
            self._send_workout_reminder,
            trigger=CronTrigger(day_of_week=dow, hour=hour, minute=minute, timezone="UTC"),
            kwargs={"telegram_id": telegram_id, "time_hhmm": time_hhmm},
            id=f"workout:{schedule_id}",
            replace_existing=True,
            misfire_grace_time=60,
        )

    async def _send_workout_reminder(self, *, telegram_id: int, time_hhmm: str) -> None:
        # Текст по ТЗ
        await self.bot.send_message(telegram_id, f"Пора качаться! 💪 Тренировка сегодня в {time_hhmm}")

    def _schedule_water_reminder(self) -> None:
        # Ежедневно в 20:00 UTC. Позже сделаем часовой пояс на пользователя.
        self.scheduler.add_job(
            self._water_reminder_job,
            trigger=CronTrigger(hour=20, minute=0, timezone="UTC"),
            id="water:remind",
            replace_existing=True,
            misfire_grace_time=300,
        )

    async def _water_reminder_job(self) -> None:
        today = dt.datetime.now(dt.timezone.utc).date()
        start = dt.datetime.combine(today, dt.time.min, tzinfo=dt.timezone.utc)
        end = dt.datetime.combine(today, dt.time.max, tzinfo=dt.timezone.utc)

        async with self.sessionmaker() as session:
            q = select(User.id, User.telegram_id, User.water_norm_ml).where(User.reminders_enabled == True)  # noqa: E712
            res = await session.execute(q)
            users = res.all()

            for user_id, telegram_id, norm in users:
                wq = select(func.coalesce(func.sum(WaterLog.amount_ml), 0)).where(WaterLog.user_id == user_id)
                wq = wq.where(WaterLog.logged_at >= start).where(WaterLog.logged_at <= end)
                wres = await session.execute(wq)
                total = int(wres.scalar_one())
                if total < int(norm):
                    await self.bot.send_message(
                        telegram_id,
                        f"💧 Напоминание: вы выпили {total} мл из {int(norm)} мл. Самое время добрать норму!",
                    )

