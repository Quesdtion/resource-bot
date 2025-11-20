import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from db.database import get_pool

from bot.handlers import (
    manager_menu,
    resource_issue,
    lifetime,
    admin_menu,
    reports,
    admin_upload,
    status_mark,  # <-- НОВЫЙ ХЕНДЛЕР СТАТУСОВ
)

from bot.middlewares.role import RoleMiddleware
from bot.utils.scheduler import setup_scheduler


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    # Инициализируем бота
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Подключение к БД
    bot.db = await get_pool()

    # Мидлварь ролей
    dp.message.middleware(RoleMiddleware())

    # Роутеры
    dp.include_router(manager_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(lifetime.router)
    dp.include_router(admin_menu.router)
    dp.include_router(reports.router)
    dp.include_router(admin_upload.router)
    dp.include_router(status_mark.router)  # <-- ПОДКЛЮЧАЕМ НОВЫЙ

    # Планировщик (если используешь)
    setup_scheduler(bot)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
