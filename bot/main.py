# bot/main.py
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from db.database import get_pool
from bot.middlewares.role import RoleMiddleware
from bot.handlers import manager_menu, admin_menu, resource_issue, status_mark, reports

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("Bot starting...")

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # один общий пул + кладём его в bot.db для мидлварей и хендлеров
    pool = await get_pool()
    bot.db = pool

    # мидлварь ролей
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    # роутеры
    dp.include_router(manager_menu.router)
    dp.include_router(admin_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(status_mark.router)
    dp.include_router(reports.router)

    logging.getLogger(__name__).info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
