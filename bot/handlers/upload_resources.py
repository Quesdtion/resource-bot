from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb

import re

router = Router()

# ------------------------------
# Кнопки
# ------------------------------

BACK_BUTTON = "⬅️ Назад"

# Типы ресурсов, которые ты используешь
RESOURCE_TYPES = ["mamba", "tabor", "beboo"]


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
async def upload_start(message: Message, state: FSMContext):
    await state.set_state(UploadStates.waiting_type)
    await message.answer("Выбери тип ресурса:", reply_markup=resource_types_kb())


@router.message(F.text == BACK_BUTTON)
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=manager_menu_kb())


# ------------------------------
# Выбор типа ресурса
# ------------------------------

@router.message(UploadStates.waiting_type)
async def choose_type(message: Message, state: FSMContext):
    r_type = message.text.strip().lower()

    if r_type not in RESOURCE_TYPES:
        await message.answer("Выбери тип кнопкой.", reply_markup=resource_types_kb())
        return

    await state.update_data(type=r_type)
    await state.set_state(UploadStates.waiting_text)

    await message.answer(
        "Отправь список ресурсов.\n"
        "Поддерживаемые форматы:\n"
        "• email password\n"
        "• email,password\n"
        "• email;password\n"
        "• email:password\n"
        "• phone:password\n"
        "• строки с лишним текстом — найдём автоматически",
        reply_markup=back_only_kb()
    )


# ------------------------------
# Парсер строки
# ------------------------------

# примитивные шаблоны для логина
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PHONE_RE = re.compile(r'\b\d{7,15}\b')


def parse_line(line: str):
    """
    Возвращает (login, password) или None

    Поддерживает:
    - логин:пароль  (в т.ч. телефон:пароль)
    - логин;пароль
    - логин,пароль
    - логин\tпароль
    - логин пароль
    - строки с лишним текстом: ищем email/телефон и первое "слово" после него
    """
    if not line:
        return None

    line = line.strip()
    if not line:
        return None

    # 1) Прямые разделители логин/пароль
    # порядок важен: сначала двоеточие и точка с запятой, потом таб/запятая/пробел
    for delim in (":", ";", ",", "\t"):
        if delim in line:
            left, right = line.split(delim, 1)
            left = left.strip()
            right = right.strip()
            if left and right:
                return left, right

    # 2) Если просто разделено пробелом(ами)
    parts = line.split()
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()

    # 3) Строки с лишним текстом.
    #    Ищем email или телефон, а потом первое "слово" после него — пароль.
    m_email = EMAIL_RE.search(line)
    if m_email:
        login = m_email.group(0)
        tail = line[m_email.end():]
        m_pass = re.search(r'([^\s|:;,\t]+)', tail)
        if m_pass:
            password = m_pass.group(1)
            return login, password

    m_phone = PHONE_RE.search(line)
    if m_phone:
        login = m_phone.group(0)
        tail = line[m_phone.end():]
        m_pass = re.search(r'([^\s|:;,\t]+)', tail)
        if m_pass:
            password = m_pass.group(1)
            return login, password

    return None


# ------------------------------
# Загрузка текста
# ------------------------------

@router.message(UploadStates.waiting_text)
async def process_upload_text(message: Message, state: FSMContext):
    # обработка кнопки "Назад" внутри состояния
    if message.text == BACK_BUTTON:
        return await back_to_menu(message, state)

    data = await state.get_data()
    r_type = data.get("type")

    lines = message.text.split("\n")
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
            reply_markup=manager_menu_kb()
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
                # дубликаты и прочие ошибки просто пропускаем
                pass

    text = (
        f"✅ Загрузка завершена.\n"
        f"Распознано пар: {total}\n"
        f"Успешно добавлено в БД: {added}\n\n"
        f"Тип: {r_type}"
    )

    await message.answer(text, reply_markup=manager_menu_kb())
    await state.clear()
