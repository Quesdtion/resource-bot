from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()

BACK_BUTTON_TEXT = "⬅️ Назад"


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Отчёт по ресурсам")],
            [KeyboardButton(text="💰 Финансовый отчёт")],
            [KeyboardButton(text="📦 Загрузить ресурсы")],
        ],
        resize_keyboard=True,
    )


async def _is_admin(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.CHECK_MANAGER_ROLE, user_id)

    return bool(row and row["role"] == "admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await _is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return

    await message.answer("Админ-меню:", reply_markup=admin_menu_kb())
