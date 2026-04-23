from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.keyboards.settings import settings_kb
from config import settings
from db.repositories.users import UsersRepository

router = Router()


@router.message(Command("settings"))
async def settings_cmd(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    await state.clear()
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)
        reminders_enabled = bool(user.reminders_enabled) if user else True
        norm = int(user.water_norm_ml) if user and user.water_norm_ml else settings.default_water_norm_ml

    await message.answer(
        "⚙️ <b>Настройки</b>\n"
        f"- Норма воды: <b>{norm} мл</b>\n"
        "- План/питание: сохраняются и не перегенерируются без команды обновления.\n",
        reply_markup=settings_kb(reminders_enabled=reminders_enabled),
    )


@router.message(F.text.in_({"⚙️ Настройки", "Настройки", "⚙️ настройки", "настройки"}))
async def settings_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    await settings_cmd(message, db_sessionmaker, state)


@router.callback_query(F.data == "settings:toggle_reminders")
async def toggle_reminders(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(cb.from_user.id)
        current = bool(user.reminders_enabled) if user else True
        await repo.set_reminders_enabled(telegram_id=cb.from_user.id, enabled=not current)
        await session.commit()

        new_val = not current
        norm = int(user.water_norm_ml) if user and user.water_norm_ml else settings.default_water_norm_ml

    await cb.message.edit_text(
        "⚙️ <b>Настройки</b>\n"
        f"- Норма воды: <b>{norm} мл</b>\n"
        "- План/питание: сохраняются и не перегенерируются без команды обновления.\n",
        reply_markup=settings_kb(reminders_enabled=new_val),
    )
    await cb.answer("Готово")


@router.callback_query(F.data == "settings:water_norm")
async def water_norm_prompt(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(settings_wait="water_norm")
    await cb.message.edit_text("Введите новую норму воды в мл (например, 2000).")
    await cb.answer()


@router.message(F.text.regexp(r"^\d{1,4}$"))
async def water_norm_input(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("settings_wait") != "water_norm":
        return

    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Нужно число в мл (например, 2000).")
        return
    norm = int(raw)
    if norm < 500 or norm > 6000:
        await message.answer("Введите значение в диапазоне 500…6000 мл.")
        return

    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        await repo.set_water_norm(telegram_id=message.from_user.id, norm_ml=norm)
        user = await repo.get_by_telegram_id(message.from_user.id)
        await session.commit()

        reminders_enabled = bool(user.reminders_enabled) if user else True

    await state.clear()
    await message.answer(
        "⚙️ <b>Настройки</b>\n"
        f"- Норма воды: <b>{norm} мл</b>\n"
        "- План/питание: сохраняются и не перегенерируются без команды обновления.\n",
        reply_markup=settings_kb(reminders_enabled=reminders_enabled),
    )

