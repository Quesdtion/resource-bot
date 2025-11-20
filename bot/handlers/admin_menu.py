from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


def admin_menu_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура админа.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Отчёт по ресурсам")],
            [KeyboardButton(text="💰 Финансовый отчёт")],
            [KeyboardButton(text="📦 Загрузить ресурсы")],
        ],
        resize_keyboard=True
    )


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """
    Открыть админ-панель, если пользователь с role='admin' в таблице managers.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.CHECK_MANAGER_ROLE, message.from_user.id)

    if not row or row["role"] != "admin":
        await message.answer("Нет доступа")
        return

    await message.answer(
        "Админ-панель. Выбери действие:",
        reply_markup=admin_menu_kb()
    )
