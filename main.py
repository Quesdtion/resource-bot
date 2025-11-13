import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.utils.db import create_pool
from bot.middlewares.role import RoleMiddleware
from bot.utils.scheduler import setup_scheduler

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    pool = await create_pool()
    dp["db"] = pool

    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    from bot.handlers import manager_menu, resource_issue, lifetime, admin_menu, reports
    dp.include_router(manager_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(lifetime.router)
    dp.include_router(admin_menu.router)
    dp.include_router(reports.router)

    setup_scheduler(dp)

    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
