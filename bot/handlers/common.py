from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.keyboards.main_menu import main_menu_kb
from bot.keyboards.quick_actions import quick_actions_kb
from bot.keyboards.registration import (
    frequency_kb,
    goal_kb,
    level_kb,
    location_kb,
    preferred_time_kb,
)
from bot.states.registration import Registration
from db.models import AIUsageLog
from db.repositories.nutrition_tips import NutritionTipsRepository
from db.repositories.schedules import SchedulesRepository
from db.repositories.water import WaterRepository
from db.repositories.workout_plans import WorkoutPlansRepository
from db.repositories.users import UsersRepository
from services.ai_service import AIService
from services.formatting import format_nutrition_text, format_workout_plan_text
from config import settings

router = Router()


def _goal_label(code: str) -> str:
    return {"lose": "Похудеть", "keep": "Поддержать форму", "gain": "Набрать массу"}.get(code, code)


def _level_label(code: str) -> str:
    return {"beginner": "Новичок", "mid": "Средний", "advanced": "Продвинутый"}.get(code, code)


def _time_label(code: str) -> str:
    return {
        "morning": "Утро (7:00–9:00)",
        "day": "День (12:00–14:00)",
        "evening": "Вечер (18:00–20:00)",
        "custom": "Своё время",
    }.get(code, code)


def _location_label(code: str) -> str:
    return {"home": "Дома", "gym": "В тренажёрном зале"}.get(code, code)


async def _build_status_text(
    *,
    telegram_id: int,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> str:
    async with db_sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(telegram_id)
        if user is None:
            return "Сначала заполните профиль: /start"

        # water today
        water = WaterRepository(session)
        import datetime as dt
        today = dt.datetime.now(dt.timezone.utc).date()
        water_total = await water.total_for_date(user_id=user.id, date=today)
        water_norm = int(user.water_norm_ml or settings.default_water_norm_ml)
        water_percent = 0 if water_norm <= 0 else min(int(water_total * 100 / water_norm), 100)

        # schedule
        schedules = SchedulesRepository(session)
        sch = await schedules.get_for_user(user_id=user.id)
        if sch:
            days = ", ".join(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][d] for d in sorted(set(sch.days_of_week)))
            sch_text = f"{days} в {sch.notify_time} ({'ВКЛ' if sch.is_active else 'ВЫКЛ'})"
        else:
            sch_text = "не настроено"

        # ai usage today
        q = (
            select(func.count(AIUsageLog.id))
            .where(AIUsageLog.user_id == user.id)
            .where(func.date(AIUsageLog.created_at) == today)
        )
        res = await session.execute(q)
        ai_used = int(res.scalar_one())
    return (
        "📊 <b>Статус</b>\n"
        f"👤 Профиль: <b>{user.goal or '—'}</b>, {user.level or '—'}\n"
        f"💧 Вода сегодня: <b>{water_total}/{water_norm} мл</b> ({water_percent}%)\n"
        f"⏰ Расписание: <b>{sch_text}</b>\n"
        f"🤖 AI-запросы сегодня: <b>{ai_used}</b> (без лимита)"
    )


@router.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with db_sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(message.from_user.id)
    if user and all([user.goal, user.level, user.frequency, user.preferred_time, user.location]):
        await state.clear()
        await message.answer(
            "С возвращением! Профиль уже заполнен ✅\nОткрыл главное меню 👇",
            reply_markup=main_menu_kb(),
        )
        return

    await state.clear()
    await state.set_state(Registration.goal)
    await message.answer(
        "Привет! Я персональный фитнес‑тренер.\n\n"
        "<b>Шаг 1/5.</b> Какова ваша цель?",
        reply_markup=goal_kb(),
    )


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(
        "Команды:\n"
        "/start — регистрация\n"
        "/profile — анкета\n"
        "/plan — план тренировок\n"
        "/plan_new — сгенерировать новый план\n"
        "/schedule — расписание\n"
        "/water — трекер воды\n"
        "/nutrition — питание\n"
        "/nutrition_new — сгенерировать новые рекомендации\n"
        "/plan_last — последний план\n"
        "/status — дашборд прогресса\n"
        "/menu — главное меню\n"
        "/profile_reset — заново пройти анкету\n"
        "/ai_test — проверка AI-подключения\n"
        "/settings — настройки\n"
        "/help — помощь"
    )


@router.message(Command("menu"))
async def menu_cmd(message: Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


@router.message(Command("profile_reset"))
async def profile_reset_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Registration.goal)
    await message.answer(
        "Запускаем повторное заполнение анкеты.\n\n<b>Шаг 1/5.</b> Какова ваша цель?",
        reply_markup=goal_kb(),
    )


@router.message(Command("status"))
async def status_cmd(
    message: Message,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    text = await _build_status_text(telegram_id=message.from_user.id, db_sessionmaker=db_sessionmaker)
    await message.answer(text, reply_markup=quick_actions_kb())


@router.message(Command("plan"))
async def plan_cmd(
    message: Message,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)

    if user is None or not all([user.goal, user.level, user.frequency, user.preferred_time, user.location]):
        await message.answer("Сначала заполните анкету: /start")
        return

    async with db_sessionmaker() as session:
        plans = WorkoutPlansRepository(session)
        latest = await plans.get_latest_for_user(user_id=user.id)
    if latest:
        text = str((latest.plan_json or {}).get("text") or "")
        await message.answer(format_workout_plan_text(text), reply_markup=quick_actions_kb())
        return

    await message.answer("Плана ещё нет, генерирую первый…")
    await _generate_new_plan(message=message, user=user, db_sessionmaker=db_sessionmaker)


async def _generate_new_plan(
    *,
    message: Message,
    user,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    ai = AIService(sessionmaker=db_sessionmaker)
    try:
        text = await ai.generate_workout_plan(user=user)
    finally:
        await ai.aclose()
    await message.answer(format_workout_plan_text(text), reply_markup=quick_actions_kb())


@router.message(Command("plan_new"))
async def plan_new_cmd(
    message: Message,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)
    if user is None or not all([user.goal, user.level, user.frequency, user.preferred_time, user.location]):
        await message.answer("Сначала заполните анкету: /start")
        return
    await message.answer("Генерирую новый план…")
    await _generate_new_plan(message=message, user=user, db_sessionmaker=db_sessionmaker)


@router.message(Command("nutrition"))
async def nutrition_cmd(
    message: Message,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)

    if user is None or not user.goal:
        await message.answer("Сначала заполните анкету: /start")
        return

    async with db_sessionmaker() as session:
        tips_repo = NutritionTipsRepository(session)
        latest = await tips_repo.get_latest_for_user(user_id=user.id)
    if latest:
        await message.answer(format_nutrition_text(latest.content), reply_markup=quick_actions_kb())
        return

    await message.answer("Рекомендаций ещё нет, генерирую первые…")
    await _generate_new_nutrition(message=message, user=user, db_sessionmaker=db_sessionmaker)


async def _generate_new_nutrition(
    *,
    message: Message,
    user,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    ai = AIService(sessionmaker=db_sessionmaker)
    try:
        text = await ai.get_nutrition_tips(user=user, force_refresh=True)
    finally:
        await ai.aclose()
    await message.answer(format_nutrition_text(text), reply_markup=quick_actions_kb())


@router.message(Command("nutrition_new"))
async def nutrition_new_cmd(
    message: Message,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)
    if user is None or not user.goal:
        await message.answer("Сначала заполните анкету: /start")
        return
    await message.answer("Генерирую новые рекомендации по питанию…")
    await _generate_new_nutrition(message=message, user=user, db_sessionmaker=db_sessionmaker)


@router.message(Command("plan_last"))
async def plan_last_cmd(
    message: Message,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with db_sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала заполните профиль: /start", reply_markup=main_menu_kb())
            return
        plans = WorkoutPlansRepository(session)
        latest = await plans.get_latest_for_user(user_id=user.id)

    if latest is None:
        await message.answer("Пока нет сохранённых планов. Сгенерируйте: /plan", reply_markup=main_menu_kb())
        return

    text = str((latest.plan_json or {}).get("text") or "")
    await message.answer(format_workout_plan_text(text), reply_markup=quick_actions_kb())


@router.message(Command("ai_test"))
async def ai_test_cmd(
    message: Message,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    await message.answer("Проверяю AI-соединение…")
    # user is optional for this check, use short synthetic prompt through same service path
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)
    if user is None or not user.goal:
        await message.answer("AI доступен, но для полной проверки сначала заполните профиль: /start")
        return

    ai = AIService(sessionmaker=db_sessionmaker)
    try:
        text = await ai.get_nutrition_tips(user=user)
    finally:
        await ai.aclose()
    if "Техническая причина" in text or "Unauthorized" in text:
        await message.answer(text)
    else:
        await message.answer("✅ AI подключен и отвечает корректно.")


@router.message(Command("profile"))
async def profile_cmd(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        user = await repo.get_by_telegram_id(message.from_user.id)

    if user is None or not all([user.goal, user.level, user.frequency, user.preferred_time, user.location]):
        await message.answer("Анкета не заполнена. Запустим регистрацию заново: /start", reply_markup=main_menu_kb())
        return

    await message.answer(
        "<b>Ваша анкета</b>\n"
        f"- Цель: <b>{user.goal}</b>\n"
        f"- Уровень: <b>{user.level}</b>\n"
        f"- Тренировки/неделю: <b>{user.frequency}</b>\n"
        f"- Время: <b>{user.preferred_time}</b>\n"
        f"- Где: <b>{user.location}</b>\n\n"
        "Чтобы обновить — нажмите /start.",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == "🏋️ План")
async def plan_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await plan_cmd(message, db_sessionmaker)


@router.message(F.text == "🥗 Питание")
async def nutrition_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await nutrition_cmd(message, db_sessionmaker)


@router.message(F.text == "👤 Профиль")
async def profile_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await profile_cmd(message, db_sessionmaker)


@router.message(F.text == "📘 Последний план")
async def plan_last_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await plan_last_cmd(message, db_sessionmaker)


@router.message(F.text == "📊 Статус")
async def status_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await status_cmd(message, db_sessionmaker)


@router.message(F.text == "🤖 AI тест")
async def ai_test_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await ai_test_cmd(message, db_sessionmaker)


@router.callback_query(F.data == "qa:plan")
async def qa_plan(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await cb.answer()
    if cb.message:
        await plan_cmd(cb.message, db_sessionmaker)


@router.callback_query(F.data == "qa:nutrition")
async def qa_nutrition(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await cb.answer()
    if cb.message:
        await nutrition_cmd(cb.message, db_sessionmaker)


@router.callback_query(F.data == "qa:plan_new")
async def qa_plan_new(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await cb.answer()
    if cb.message:
        await plan_new_cmd(cb.message, db_sessionmaker)


@router.callback_query(F.data == "qa:nutrition_new")
async def qa_nutrition_new(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await cb.answer()
    if cb.message:
        await nutrition_new_cmd(cb.message, db_sessionmaker)


@router.callback_query(F.data == "qa:status")
async def qa_status(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    await cb.answer()
    text = await _build_status_text(telegram_id=cb.from_user.id, db_sessionmaker=db_sessionmaker)
    if cb.message:
        await cb.message.answer(text, reply_markup=quick_actions_kb())


@router.callback_query(F.data == "qa:water")
async def qa_water(cb: CallbackQuery) -> None:
    await cb.answer("Откройте /water или кнопку «💧 Вода» в меню")


@router.callback_query(Registration.goal, F.data.startswith("reg_goal:"))
async def reg_goal(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":", 1)[1]
    await state.update_data(goal=_goal_label(code), goal_code=code)
    await state.set_state(Registration.level)
    await cb.message.edit_text("<b>Шаг 2/5.</b> Ваш уровень подготовки?", reply_markup=level_kb())
    await cb.answer()


@router.callback_query(Registration.level, F.data.startswith("reg_level:"))
async def reg_level(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":", 1)[1]
    await state.update_data(level=_level_label(code), level_code=code)
    await state.set_state(Registration.frequency)
    await cb.message.edit_text(
        "<b>Шаг 3/5.</b> Сколько раз в неделю готовы тренироваться?",
        reply_markup=frequency_kb(),
    )
    await cb.answer()


@router.callback_query(Registration.frequency, F.data.startswith("reg_freq:"))
async def reg_frequency(cb: CallbackQuery, state: FSMContext) -> None:
    freq = int(cb.data.split(":", 1)[1])
    await state.update_data(frequency=freq)
    await state.set_state(Registration.preferred_time)
    await cb.message.edit_text(
        "<b>Шаг 4/5.</b> В какое время удобно тренироваться?",
        reply_markup=preferred_time_kb(),
    )
    await cb.answer()


@router.callback_query(Registration.preferred_time, F.data.startswith("reg_time:"))
async def reg_time(cb: CallbackQuery, state: FSMContext) -> None:
    code = cb.data.split(":", 1)[1]
    if code == "custom":
        await state.update_data(preferred_time=_time_label(code), preferred_time_code=code)
        await cb.message.edit_text("Напишите удобное время в формате <b>HH:MM</b> (например, 19:30).")
        await cb.answer()
        return

    await state.update_data(preferred_time=_time_label(code), preferred_time_code=code)
    await state.set_state(Registration.location)
    await cb.message.edit_text("<b>Шаг 5/5.</b> Где вы занимаетесь?", reply_markup=location_kb())
    await cb.answer()


@router.message(Registration.preferred_time)
async def reg_time_custom(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    # Minimal validation for MVP: HH:MM
    if len(text) != 5 or text[2] != ":" or not text.replace(":", "").isdigit():
        await message.answer("Пожалуйста, пришлите время в формате <b>HH:MM</b> (например, 07:30).")
        return

    hh = int(text[:2])
    mm = int(text[3:])
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        await message.answer("Время выглядит некорректно. Пример: <b>19:30</b>.")
        return

    await state.update_data(preferred_time=text, preferred_time_code="custom")
    await state.set_state(Registration.location)
    await message.answer("<b>Шаг 5/5.</b> Где вы занимаетесь?", reply_markup=location_kb())


@router.callback_query(Registration.location, F.data.startswith("reg_loc:"))
async def reg_location(cb: CallbackQuery, state: FSMContext, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    code = cb.data.split(":", 1)[1]
    data = await state.get_data()
    profile = {
        "goal": data["goal"],
        "level": data["level"],
        "frequency": data["frequency"],
        "preferred_time": data["preferred_time"],
        "location": _location_label(code),
    }

    async with db_sessionmaker() as session:
        repo = UsersRepository(session)
        await repo.upsert_profile(
            telegram_id=cb.from_user.id,
            name=cb.from_user.full_name,
            goal=profile["goal"],
            level=profile["level"],
            frequency=profile["frequency"],
            preferred_time=profile["preferred_time"],
            location=profile["location"],
        )
        await session.commit()

    await state.clear()
    await cb.message.edit_text(
        "Готово! Анкета сохранена.\n\n"
        "<b>Ваш профиль</b>\n"
        f"- Цель: <b>{profile['goal']}</b>\n"
        f"- Уровень: <b>{profile['level']}</b>\n"
        f"- Тренировки/неделю: <b>{profile['frequency']}</b>\n"
        f"- Время: <b>{profile['preferred_time']}</b>\n"
        f"- Где: <b>{profile['location']}</b>\n\n"
        "Дальше можно запросить план: /plan",
    )
    await cb.message.answer("Открыл главное меню 👇", reply_markup=main_menu_kb())
    await cb.answer()

