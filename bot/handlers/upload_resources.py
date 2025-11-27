# bot/handlers/upload_resources.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb
from bot.utils.admin_stats import send_free_resources_stats

router = Router()

# ------------------------------
# Кнопки
# ------------------------------

BACK_BUTTON = "⬅️ Назад"

# Все типы ресурсов
RESOURCE_TYPES = ["mamba", "tabor", "beboo", "rambler"]


def resource_types_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t) for t in RESOURCE_TYPES],
            [KeyboardButton(text=BACK_BUTTON)],
        ],
        resize_keyboard=True,
    )


def back_only_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BUTTON)]],
        resize_keyboard=True,
    )


# ------------------------------
# FSM
# ------------------------------


class UploadStates(StatesGroup):
    waiting_type = State()
    waiting_text = State()


# ------------------------------
# Команда загрузки
# ------------------------------


@router.message(F.text == "📦 Загрузить ресурсы")
async def upload_start(message: Message, state: FSMContext, role: str | None = None):
    """
    Вход в загрузку ресурсов из админ-меню.
    """
    await state.set_state(UploadStates.waiting_type)
    await message.answer("Выбери тип ресурса:", reply_markup=resource_types_kb())


@router.message(F.text == BACK_BUTTON)
async def back_to_menu(message: Message, state: FSMContext):
    """
    Глобальная кнопка Назад для сценария загрузки:
    очищаем стейт и возвращаем в обычное меню.
    """
    await state.clear()
    await message.answer("Главное меню", reply_markup=manager_menu_kb())


# ------------------------------
# Выбор типа ресурса
# ------------------------------


@router.message(UploadStates.waiting_type)
async def choose_type(message: Message, state: FSMContext):
    r_type = (message.text or "").strip().lower()

    if r_type not in RESOURCE_TYPES:
        await message.answer("Выбери тип кнопкой.", reply_markup=resource_types_kb())
        return

    await state.update_data(type=r_type)
    await state.set_state(UploadStates.waiting_text)

    await message.answer(
        "Отправь список ресурсов.\n"
        "Поддерживаемые форматы, например:\n"
        "• email password\n"
        "• email,password\n"
        "• email;password\n"
        "• email:password\n"
        "• phone:password\n"
        "• Логин: email | Пароль: pass | любой текст\n"
        "• строки с лишним текстом — найдём автоматически",
        reply_markup=back_only_kb(),
    )


# ------------------------------
# Парсер строки
# ------------------------------


def parse_line(line: str):
    """
    Пытается вытащить (login, password) из строки.
    Поддерживает:
      - разделители: пробел, таб, запятая, точка с запятой, двоеточие, вертикальная черта
      - строки с лишним текстом, вроде:
        'Логин: xxx | Пароль: yyy | Спасибо за покупку!'
    Логика: режем по всем разделителям, выбрасываем слова 'логин', 'пароль',
    'login', 'password', 'спасибо', 'покупку' и т.п. — берём первые два
    нормальных токена как логин и пароль.
    """
    if not line:
        return None

    original = line.strip()
    if not original:
        return None

    # Заменяем всё, что может быть разделителем, на пробел
    separators = ["\t", "|", ";", ":", ",", "/"]
    temp = original
    for sep in separators:
        temp = temp.replace(sep, " ")

    # Разбиваем по пробелам
    raw_tokens = temp.split()
    if len(raw_tokens) < 2:
        return None

    # Ключевые слова, которые нужно выкинуть
    keywords = {
        "логин",
        "пароль",
        "password",
        "pass",
        "login",
        "спасибо",
        "покупку",
        "покупки",
        "за",
        "спасибозапокупку",
    }

    tokens: list[str] = []
    for t in raw_tokens:
        low = t.lower()
        # убираем служебные слова
        if low in keywords:
            continue
        # убираем чисто смайлики/картинки и совсем мусор
        if not any(ch.isalnum() or ch in "@._-" for ch in t):
            continue
        tokens.append(t)

    if len(tokens) < 2:
        return None

    login = tokens[0].strip()
    password = tokens[1].strip()

    if not login or not password:
        return None

    return login, password


# ------------------------------
# Загрузка текста
# ------------------------------


@router.message(UploadStates.waiting_text)
async def process_upload_text(
    message: Message,
    state: FSMContext,
    role: str | None = None,
):
    # Обработка кнопки Назад внутри сценария
    if message.text == BACK_BUTTON:
        return await back_to_menu(message, state)

    data = await state.get_data()
    r_type = data.get("type")

    lines = (message.text or "").split("\n")
    parsed: list[tuple[str, str]] = []

    for ln in lines:
        res = parse_line(ln)
        if res:
            login, password = res
            parsed.append((login, password))

    total = len(parsed)
    added = 0

    if total == 0:
        await message.answer(
            "❗ Не найдено ни одной пары логин/пароль.",
            reply_markup=manager_menu_kb(),
        )
        await state.clear()
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        for login, password in parsed:
            try:
                await conn.execute(
                    """
                    INSERT INTO resources (type, login, password, buy_price, status)
                    VALUES ($1, $2, $3, 0, 'free')
                    """,
                    r_type,
                    login,
                    password,
                )
                added += 1
            except Exception:
                # Например, дубликаты по уникальному ограничению — просто пропускаем
                continue

    text = (
        f"✅ Загрузка завершена.\n"
        f"Распознано пар: {total}\n"
        f"Успешно добавлено в БД: {added}\n\n"
        f"Тип: {r_type}"
    )

    await message.answer(text, reply_markup=manager_menu_kb())
    await state.clear()

    # После загрузки — показать статистику только админу
    if role == "admin":
        await send_free_resources_stats(message)
