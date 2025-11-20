from aiogram import Router
from aiogram.filters import CommandStart, Command, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


def manager_menu_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура менеджера.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Получить ресурсы")],
            [KeyboardButton(text="📋 Мои ресурсы")],
            [KeyboardButton(text="⏱ Отметить срок жизни")],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Стартовое сообщение для менеджера.
    """
    await message.answer(
        "👋 Привет! Это бот выдачи ресурсов.\n"
        "Выбери действие на клавиатуре ниже:",
        reply_markup=manager_menu_kb(),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """
    Команда /menu — повторно показать меню.
    """
    await message.answer("Выбери действие:", reply_markup=manager_menu_kb())


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    """
    Показать Telegram ID (для добавления в managers).
    """
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>")


@router.message(F.text == "📋 Мои ресурсы")
async def my_resources(message: Message):
    """
    Мини-кабинет менеджера: показать все активные ресурсы (status = 'busy').
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.GET_ISSUED_RESOURCES, message.from_user.id)

    if not rows:
        await message.answer("У тебя сейчас нет активных ресурсов.")
        return

    lines = ["📋 Твои активные ресурсы:\n"]
    for r in rows:
        login = r["login"]
        password = r["password"]
        proxy = r["proxy"]
        r_type = r["type"]

        line = f"• <b>{r_type}</b> — <code>{login}</code> | <code>{password}</code>"
        if proxy:
            line += f" | proxy: <code>{proxy}</code>"
        lines.append(line)

    await message.answer("\n".join(lines))
