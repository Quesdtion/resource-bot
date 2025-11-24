from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb

router = Router()

# ------------------------------
# Кнопки
# ------------------------------

BACK_BUTTON = "⬅️ Назад"

RESOURCE_TYPES = ["mamba", "tabor", "beboo", "rambler"]


def resource_types_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t) for t in RESOURCE_TYPES],
            [KeyboardButton(text=BACK_BUTTON)],
        ],
        resize_keyboard=True,
    )


def back_only_kb():
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
        "• email:password\n"
        "• email\tpassword\n"
        "• строки с лишним текстом — найдём автоматически",
        reply_markup=back_only_kb()
    )


# ------------------------------
# Парсер строки
# ------------------------------

def parse_line(line: str):
    """
    Возвращает (login, password)
    Поддерживаемые типы разделителей:
    - :
    - таб
    - пробел
    - запятая
    - любые строки с мусором
    """
    line = line.strip()

    # 1) login:password
    if ":" in line:
        parts = line.split(":")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()

    # 2) TAB
    if "\t" in line:
        parts = line.split("\t")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()

    # 3) email,password
    if "," in line:
        parts = line.split(",")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()

    # 4) email password
    parts = line.split()
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()

    return None


# ------------------------------
# Загрузка текста
# ------------------------------

@router.message(UploadStates.waiting_text)
async def process_upload_text(message: Message, state: FSMContext):
    if message.text == BACK_BUTTON:
        return await back_to_menu(message, state)

    data = await state.get_data()
    r_type = data.get("type")

    lines = message.text.split("\n")
    parsed = []

    for ln in lines:
        res = parse_line(ln)
        if res:
            login, password = res
            parsed.append((login, password))

    total = len(parsed)
    added = 0

    if total == 0:
        await message.answer("❗ Не найдено ни одной пары логин/пароль.", reply_markup=manager_menu_kb())
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
                pass

    text = (
        f"✅ Загрузка завершена.\n"
        f"Распознано пар: {total}\n"
        f"Успешно добавлено в БД: {added}\n\n"
        f"Тип: {r_type}"
    )

    await message.answer(text, reply_markup=manager_menu_kb())
    await state.clear()
