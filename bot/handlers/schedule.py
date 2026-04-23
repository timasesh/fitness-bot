from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.keyboards.schedule import DAY_LABELS, schedule_days_kb, schedule_toggle_kb
from db.repositories.schedules import SchedulesRepository
from db.repositories.users import UsersRepository

router = Router()


TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _days_text(days: list[int]) -> str:
    return ", ".join(DAY_LABELS[d] for d in sorted(set(days)))


@router.message(Command("schedule"))
async def schedule_cmd(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    await state.clear()
    async with db_sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала заполните анкету: /start")
            return
        repo = SchedulesRepository(session)
        sch = await repo.get_for_user(user_id=user.id)

    if sch:
        await state.update_data(sch_days=set(sch.days_of_week), sch_time=sch.notify_time, sch_active=sch.is_active)
        await message.answer(
            "⏰ <b>Расписание тренировок</b>\n"
            f"- Дни: <b>{_days_text(sch.days_of_week)}</b>\n"
            f"- Время: <b>{sch.notify_time}</b>\n",
            reply_markup=schedule_toggle_kb(sch.is_active),
        )
        await message.answer("Выберите дни недели для напоминаний:", reply_markup=schedule_days_kb(set(sch.days_of_week)))
        await message.answer("И отправьте время в формате <b>HH:MM</b> (например, 19:00).")
        return

    # default: weekdays + 19:00
    await state.update_data(sch_days={0, 2, 4}, sch_time="19:00", sch_active=True)
    await message.answer("Выберите дни недели для напоминаний:", reply_markup=schedule_days_kb({0, 2, 4}))
    await message.answer("Теперь отправьте время в формате <b>HH:MM</b> (например, 19:00).")


@router.message(F.text.in_({"⏰ Расписание", "Расписание", "⏰ расписание", "расписание"}))
async def schedule_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    await schedule_cmd(message, db_sessionmaker, state)


@router.callback_query(F.data.startswith("sch:day:"))
async def toggle_day(cb: CallbackQuery, state: FSMContext) -> None:
    day = int(cb.data.split(":")[-1])
    data = await state.get_data()
    selected: set[int] = set(data.get("sch_days") or set())
    if day in selected:
        selected.remove(day)
    else:
        selected.add(day)
    await state.update_data(sch_days=selected)
    await cb.message.edit_reply_markup(reply_markup=schedule_days_kb(selected))
    await cb.answer()


@router.callback_query(F.data == "sch:toggle")
async def toggle_active(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    active = bool(data.get("sch_active", True))
    active = not active
    await state.update_data(sch_active=active)
    await cb.message.edit_reply_markup(reply_markup=schedule_toggle_kb(active))
    await cb.answer("Готово")


@router.message(F.text.regexp(r"^(?:[01]\d|2[0-3]):[0-5]\d$"))
async def schedule_time_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if "sch_days" not in data:
        return
    text = (message.text or "").strip()
    if not TIME_RE.match(text):
        await message.answer("Время нужно в формате <b>HH:MM</b> (например, 07:30).")
        return
    await state.update_data(sch_time=text)
    await message.answer("Ок. Теперь нажмите <b>Сохранить</b> под выбором дней.")


@router.callback_query(F.data == "sch:save")
async def schedule_save(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    data = await state.get_data()
    selected: set[int] = set(data.get("sch_days") or set())
    notify_time: str | None = data.get("sch_time")
    is_active = bool(data.get("sch_active", True))

    if not selected:
        await cb.answer("Выберите хотя бы 1 день", show_alert=True)
        return
    if not notify_time or not TIME_RE.match(notify_time):
        await cb.answer("Сначала отправьте время HH:MM", show_alert=True)
        return

    async with db_sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(cb.from_user.id)
        if user is None:
            await cb.answer("Сначала /start", show_alert=True)
            return

        repo = SchedulesRepository(session)
        await repo.upsert(
            user_id=user.id,
            days_of_week=sorted(selected),
            notify_time=notify_time,
            is_active=is_active,
        )
        await session.commit()

    await state.clear()
    await cb.message.edit_text(
        "✅ <b>Расписание сохранено</b>\n"
        f"- Дни: <b>{_days_text(sorted(selected))}</b>\n"
        f"- Время: <b>{notify_time}</b>\n"
        f"- Статус: <b>{'ВКЛ' if is_active else 'ВЫКЛ'}</b>\n\n"
        "Напоминания начнут приходить автоматически.",
    )
    await cb.answer("Сохранено")

