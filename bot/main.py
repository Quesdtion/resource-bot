import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.config import BOT_TOKEN
from db.database import get_pool

from bot.handlers import (
    manager_menu,
    resource_issue,
    lifetime,
    admin_menu,
    reports,
    import_resources,
)

logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан!")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()

    # Инициируем подключение к базе
    bot.db = await get_pool()

    # Подключаем роутеры
    dp.include_router(manager_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(lifetime.router)
    dp.include_router(admin_menu.router)
    dp.include_router(reports.router)
    dp.include_router(import_resources.router)

    print("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
