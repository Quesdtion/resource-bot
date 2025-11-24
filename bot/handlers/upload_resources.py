# bot/handlers/upload_resources.py

from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from db.database import get_pool

router = Router()

# --- Константы ---

# Типы ресурсов, которые ты используешь
RESOURCE_TYPES = ["mamba", "tabor", "beboo"]

BACK_BUTTON_TEXT = "⬅️ Назад"
UPLOAD_MENU_BUTTON_TEXT = "📦 Загрузить ресурсы"


# --- Клавиатуры ---

def upload_type_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора типа ресурса + кнопка Назад.
    """
    row_types: list[KeyboardButton] = [
        KeyboardButton(text=t) for t in RESOURCE_TYPES
    ]

    return ReplyKeyboardMarkup(
        keyboard=[
            row_types,
            [KeyboardButton(text=BACK_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )


def back_only_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BUTTON_TEXT)]],
        resize_keyboard=True,
    )


# --- FSM ---

class UploadStates(StatesGroup):
    waiting_type = State()
    waiting_text = State()


# --- Парсер входного текста ---

def parse_login_pass_pairs(raw: str) -> list[tuple[str, str]]:
    """
    Универсальный парсер пачки логин:пароль.

    Поддерживает:
    1) "email;pass"
    2) "email:pass"
    3) "email pass" (через пробел / таб)
    4) CSV: "email,pass"
    5) С лишним текстом:
       "Логин: xxx | Пароль: yyy | Спасибо..."
    """

    pairs: list[tuple[str, str]] = []

    # Разбиваем по строкам
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        # 5) Формат с "Логин:" и "Пароль:"
        if "логин" in line.lower() and "пароль" in line.lower():
            # пример: "Логин: xxx | Пароль: yyy | ..."
            # Разделим по "логин"/"пароль" грубо
            import re

            # вытащим всё, что похоже на "что-то не пробельное" вокруг двоеточий
            log_match = re.search(r"[Лл]огин[:\s]+(\S+)", line)
            pass_match = re.search(r"[Пп]ароль[:\s]+(\S+)", line)

            if log_match and pass_match:
                login = log_match.group(1)
                password = pass_match.group(1)
                pairs.append((login, password))
                continue

        # 1–4) обычные разделители
        for sep in [";", ":", ",", "\t", " "]:
            if sep in line:
                parts = [p for p in line.split(sep) if p]
                if len(parts) >= 2:
                    login = parts[0].strip()
                    password = parts[1].strip()
                    if login and password:
                        pairs.append((login, password))
                break

    return pairs


# --- Хендлеры ---

@router.message(F.text == UPLOAD_MENU_BUTTON_TEXT)
async def start_upload(message: Message, state: FSMContext, role: str | None = None):
    """
    Вход в загрузку ресурсов из админ-меню.
    """
    if role != "admin":
        await message.answer("❌ У тебя нет доступа к загрузке ресурсов.")
        return

    await state.set_state(UploadStates.waiting_type)
    await message.answer(
        "Выбери тип ресурса, который загружаешь:",
        reply_markup=upload_type_kb(),
    )


@router.message(UploadStates.waiting_type, F.text == BACK_BUTTON_TEXT)
async def cancel_upload_from_type(message: Message, state: FSMContext):
    """
    Назад с шага выбора типа → просто выходим из FSM.
    Админ дальше может сам нажать нужную кнопку меню.
    """
    await state.clear()
    await message.answer("Загрузка отменена.", reply_markup=back_only_kb())


@router.message(UploadStates.waiting_type, F.text.in_(RESOURCE_TYPES))
async def choose_type(message: Message, state: FSMContext):
    """
    Админ выбрал тип (mamba / tabor / beboo).
    """
    r_type = message.text.strip()
    await state.update_data(resource_type=r_type)
    await state.set_state(UploadStates.waiting_text)

    await message.answer(
        "Отправь текстом пачку логин:пароль.\n\n"
        "Поддерживаемые форматы строк:\n"
        "• <code>email;pass</code>\n"
        "• <code>email:pass</code>\n"
        "• <code>email pass</code>\n"
        "• <code>email,pass</code>\n"
        "• <code>Логин: xxx | Пароль: yyy | ...</code>\n\n"
        "Каждая пара — с новой строки.",
        reply_markup=back_only_kb(),
    )


@router.message(UploadStates.waiting_text, F.text == BACK_BUTTON_TEXT)
async def back_to_type(message: Message, state: FSMContext):
    """
    Назад с шага ввода текста → снова выбор типа.
    """
    await state.set_state(UploadStates.waiting_type)
    await message.answer(
        "Выбери тип ресурса, который загружаешь:",
        reply_markup=upload_type_kb(),
    )


@router.message(UploadStates.waiting_text)
async def process_upload_text(message: Message, state: FSMContext):
    """
    Получаем пачку текста, парсим, сохраняем в БД.
    """
    data = await state.get_data()
    r_type: str = data.get("resource_type", "unknown")

    raw_text = message.text or ""
    pairs = parse_login_pass_pairs(raw_text)

    if not pairs:
        await message.answer(
            "❌ Не удалось распознать ни одной пары логин:пароль.\n"
            "Проверь формат и попробуй ещё раз.",
            reply_markup=back_only_kb(),
        )
        return

    pool = await get_pool()
    inserted = 0

    async with pool.acquire() as conn:
        for login, password in pairs:
            # Проверим, нет ли уже такого ресурса
            exists = await conn.fetchval(
                """
                SELECT 1 FROM resources
                WHERE type = $1 AND login = $2 AND password = $3
                """,
                r_type,
                login,
                password,
            )
            if exists:
                continue

            # Вставляем минимальный набор полей.
            await conn.execute(
                """
                INSERT INTO resources (type, login, password, status)
                VALUES ($1, $2, $3, 'free')
                """,
                r_type,
                login,
                password,
            )
            inserted += 1

    await state.clear()

    await message.answer(
        "✅ Загрузка завершена.\n"
        f"Распознано пар: <b>{len(pairs)}</b>\n"
        f"Успешно добавлено в БД: <b>{inserted}</b>\n\n"
        f"Тип: <b>{r_type}</b>",
        reply_markup=back_only_kb(),
    )
