# bot/main.py
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from db.database import get_pool
from bot.middlewares.role import RoleMiddleware
from bot.handlers import (
    manager_menu,
    admin_menu,
    resource_issue,
    status_mark,
    reports,
    upload_resources,   # 🔹 наш новый модуль
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Bot starting...")

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # общий пул БД
    bot.db = await get_pool()

    # мидлварь ролей
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    # роутеры
    dp.include_router(manager_menu.router)
    dp.include_router(admin_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(status_mark.router)
    dp.include_router(reports.router)
    dp.include_router(upload_resources.router)  # 🔹 подключаем загрузку

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
