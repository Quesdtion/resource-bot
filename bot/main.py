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

    # Создаём бота
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

    # Создаём пул подключений к БД и вешаем на бота
    pool = await create_pool()
    # теперь в любом хендлере можно будет получить доступ как message.bot.db
    setattr(bot, "db", pool)

    # Диспетчер
    dp = Dispatcher(storage=MemoryStorage())

    # Мидлварь с ролями
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    # Роутеры
    from bot.handlers import manager_menu, resource_issue, lifetime, admin_menu, reports, import_resources
...
    dp.include_router(manager_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(lifetime.router)
    dp.include_router(admin_menu.router)
    dp.include_router(reports.router)
    dp.include_router(import_resources.router)


    # Планировщик (заглушка)
    setup_scheduler(dp)

    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
