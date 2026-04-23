import asyncio
import logging

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import common as common_handlers
from bot.handlers import schedule as schedule_handlers
from bot.handlers import settings as settings_handlers
from bot.handlers import water as water_handlers
from config import settings
from db.models import Base
from db.session import create_engine_and_sessionmaker
from services.scheduler import SchedulerService


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


async def main() -> None:
    setup_logging()

    storage = MemoryStorage()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)

    engine, sessionmaker = create_engine_and_sessionmaker(settings.database_url)
    # Дадим aiogram доступ к зависимостям для инъекции в хендлеры
    dp["db_sessionmaker"] = sessionmaker
    # Автосоздание таблиц (SQLite) при первом запуске
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    dp.include_router(common_handlers.router)
    dp.include_router(schedule_handlers.router)
    dp.include_router(water_handlers.router)
    dp.include_router(settings_handlers.router)

    scheduler = SchedulerService(bot=bot, sessionmaker=sessionmaker)
    await scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        await scheduler.shutdown()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
