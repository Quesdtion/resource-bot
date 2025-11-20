import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.handlers import manager_menu, resource_issue, lifetime, admin_menu, reports
from bot.middlewares.role import RoleMiddleware
from bot.utils.scheduler import setup_scheduler


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    # Инициализируем бота и диспетчер
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Мидлварь ролей (manager / admin), как и раньше
    dp.message.middleware(RoleMiddleware())

    # Подключаем все роутеры
    dp.include_router(manager_menu.router)
    dp.include_router(resource_issue.router)
    dp.include_router(lifetime.router)
    dp.include_router(admin_menu.router)
    dp.include_router(reports.router)

    # Запуск планировщика фоновых задач (отчёты и т.п.)
    setup_scheduler(bot)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
