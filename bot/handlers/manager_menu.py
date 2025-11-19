from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()


def get_manager_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура менеджера (основное меню).
    """
    kb = [
        [KeyboardButton(text="📦 Получить ресурс")],
        [KeyboardButton(text="⏱ Отметить срок жизни")],
        [KeyboardButton(text="📋 Мои ресурсы")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Стартовое сообщение для пользователя/менеджера.
    """
    text = (
        "👋 Привет! Это бот выдачи ресурсов.\n"
        "Выбери действие на клавиатуре ниже:"
    )
    await message.answer(text, reply_markup=get_manager_keyboard())


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """
    Команда /menu — просто повторно показывает клавиатуру.
    """
    await message.answer("Выбери действие:", reply_markup=get_manager_keyboard())


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    """
    Служебная команда — показать Telegram ID пользователя.
    Нужна, чтобы удобно занести ID в таблицу managers как admin/manager.
    """
    await message.answer(
        f"Твой Telegram ID: <code>{message.from_user.id}</code>"
    )
