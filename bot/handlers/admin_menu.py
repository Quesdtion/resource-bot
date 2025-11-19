from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from db.database import get_pool

router = Router()

# Клавиатура админа
admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Отчёт по ресурсам")],
        [KeyboardButton(text="💰 Финансовый отчёт")],
    ],
    resize_keyboard=True
)


async def is_admin(user_id: int) -> bool:
    """
    Проверяем роль пользователя в таблице managers.
    tg_id = user_id, роль должна быть 'admin'
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT role FROM managers WHERE tg_id = $1",
            user_id
        )
    return row is not None and row["role"] == "admin"


@router.message(F.text == "/admin")
@router.message(F.text == "⚙ Админ-панель")
async def admin_start(message: Message):
    # Проверяем права
    if not await is_admin(message.from_user.id):
        await message.answer("У тебя нет доступа к админ-панели.")
        return

    await message.answer(
        "Админ-панель. Выбери действие:",
        reply_markup=admin_kb
    )
