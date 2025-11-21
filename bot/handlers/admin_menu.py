from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from bot.handlers.manager_menu import manager_menu_kb, ADMIN_MENU_BUTTON_TEXT

router = Router()

EXIT_ADMIN_BUTTON_TEXT = "⬅️ Выйти в обычное меню"


def admin_menu_kb() -> ReplyKeyboardMarkup:
    """
    Главное меню админа.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📦 Загрузить ресурсы"),
                KeyboardButton(text="📊 Отчёты"),
            ],
            [
                KeyboardButton(text=EXIT_ADMIN_BUTTON_TEXT),
            ],
        ],
        resize_keyboard=True,
    )


async def _open_admin_menu(message: Message, role: str | None):
    """
    Общая функция входа в админ-меню.
    role передаёт мидлварь (admin / manager / None).
    """
    if role != "admin":
        await message.answer("❌ У тебя нет доступа к админ-меню.")
        return

    await message.answer(
        "👑 Админ-меню.\nВыбери действие:",
        reply_markup=admin_menu_kb(),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, role: str | None = None):
    await _open_admin_menu(message, role)


@router.message(F.text == ADMIN_MENU_BUTTON_TEXT)
async def btn_admin_menu(message: Message, role: str | None = None):
    """
    Обработка кнопки 🛠 Админ меню из обычного меню.
    """
    await _open_admin_menu(message, role)


@router.message(F.text == EXIT_ADMIN_BUTTON_TEXT)
async def exit_admin_menu(message: Message, role: str | None = None):
    """
    Кнопка выхода из админки обратно в обычное меню.
    """
    await message.answer(
        "Возвращаю в обычное меню:",
        reply_markup=manager_menu_kb(),
    )
