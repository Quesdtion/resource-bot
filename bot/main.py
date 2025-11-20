import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from db.database import get_pool

from bot.handlers import (
    manager_menu,
    resource_issue,
    admin_menu,
    reports,
    admin_upload,
    status_mark,
)

from bot.middlewares.role import RoleMiddleware
from bot.utils.scheduler import setup_scheduler


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Инициализируем пул БД
    await get_pool()

    # Мидлварь ролей
    dp.message.middleware(RoleMiddleware())

    # Подключаем роутеры
    dp.include_router(manager_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(admin_menu.router)
    dp.include_router(reports.router)
    dp.include_router(admin_upload.router)
    dp.include_router(status_mark.router)

    # Планировщик, если используешь
    setup_scheduler(bot)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
