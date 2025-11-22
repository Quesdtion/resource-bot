from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()

BACK_BUTTON_TEXT = "⬅️ Назад"
ADMIN_MENU_BUTTON_TEXT = "🛠 Админ меню"


def manager_menu_kb() -> ReplyKeyboardMarkup:
    """
    Главное меню менеджера (и админа, если он работает как менеджер).
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📦 Получить ресурсы"),
                KeyboardButton(text="📋 Мои ресурсы"),
            ],
            [
                KeyboardButton(text="⚙️ Статус ресурса"),
                KeyboardButton(text="🔄 Обновить меню"),
            ],
            [
                KeyboardButton(text=ADMIN_MENU_BUTTON_TEXT),
            ],
        ],
        resize_keyboard=True,
    )


async def _send_long_text(
    message: Message,
    text: str,
    reply_markup: ReplyKeyboardMarkup | None = None,
) -> None:
    """
    Отправка длинного текста частями, чтобы не ловить
    TelegramBadRequest: message is too long.
    """
    MAX_LEN = 3500  # запас до лимита 4096

    first = True
    rest = text

    while rest:
        chunk = rest[:MAX_LEN]
        if len(rest) > MAX_LEN:
            # стараемся резать по строкам
            last_n = chunk.rfind("\n")
            if last_n > 0:
                chunk = rest[:last_n]
                rest = rest[last_n + 1 :]
            else:
                rest = rest[MAX_LEN:]
        else:
            rest = ""

        await message.answer(
            chunk,
            reply_markup=reply_markup if first else None,
        )
        first = False


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Это бот выдачи и учёта ресурсов.\n"
        "Выбери действие на клавиатуре ниже:",
        reply_markup=manager_menu_kb(),
    )


@router.message(Command("menu"))
@router.message(F.text == "🔄 Обновить меню")
async def cmd_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=manager_menu_kb())


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>")


@router.message(F.text == "📋 Мои ресурсы")
async def my_resources(message: Message):
    """
    Показать выданные ресурсы текущего менеджера.
    Если ресурсов много — разбиваем ответ на несколько сообщений.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.GET_ISSUED_RESOURCES, message.from_user.id)

    if not rows:
        await message.answer("У тебя сейчас нет активных ресурсов.")
        return

    lines: list[str] = ["📋 Твои активные ресурсы:\n"]
    for r in rows:
        login = r["login"]
        password = r["password"]
        proxy = r["proxy"]
        r_type = r["type"]

        line = f"• <b>{r_type}</b> — <code>{login}</code> | <code>{password}</code>"
        if proxy:
            line += f" | proxy: <code>{proxy}</code>"
        lines.append(line)

    full_text = "\n".join(lines)
    await _send_long_text(message, full_text)
