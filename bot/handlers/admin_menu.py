from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from bot.utils.queries import DBQueries
from db.database import get_pool

router = Router()

# Клавиатура админа
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Отчёт по ресурсам")],
        [KeyboardButton(text="💰 Финансовый отчёт")],
    ],
    resize_keyboard=True,
)


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """
    Открывает админ-панель, если пользователь есть в таблице managers с role='admin'
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.CHECK_MANAGER_ROLE, message.from_user.id)

    if not row or row["role"] != "admin":
        await message.answer("Нет доступа")
        return

    await message.answer(
        "Админ-панель. Выбери действие:",
        reply_markup=admin_keyboard,
    )
