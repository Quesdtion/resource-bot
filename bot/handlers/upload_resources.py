# bot/handlers/upload_resources.py

from __future__ import annotations

from aiogram import Router, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb, BACK_BUTTON_TEXT

router = Router()


# --------- СТЕЙТЫ --------- #

class UploadStates(StatesGroup):
    CHOOSE_TYPE = State()
    ENTER_DATA = State()


# --------- КНОПКИ / КЛАВИАТУРЫ --------- #

# типы ресурсов, которые можно выбрать кнопкой.
# при желании допиши сюда свои варианты.
RESOURCE_TYPES = [
    "mamba",
    "beboo",
    "badoo",
    "loveplanet",
]


def types_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора типа ресурса.
    """
    row_types = [KeyboardButton(text=t) for t in RESOURCE_TYPES]
    return ReplyKeyboardMarkup(
        keyboard=[
            row_types,
            [KeyboardButton(text=BACK_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура только с кнопкой 'Назад'.
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BUTTON_TEXT)]],
        resize_keyboard=True,
    )


# --------- ПАРСЕР ТЕКСТА --------- #

def _clean_piece(piece: str) -> str:
    """
    Убираем слова 'Логин:', 'Пароль:' и хвост типа 'Спасибо за покупку!❤️'.
    """
    piece = piece.strip()

    lowers = piece.lower()
    for prefix in ("логин:", "login:", "email:", "почта:"):
        if lowers.startswith(prefix):
            piece = piece[len(prefix):].strip()
            break

    for prefix in ("пароль:", "password:", "pass:"):
        if lowers.startswith(prefix):
            piece = piece[len(prefix):].strip()
            break

    # Отрезаем хвост после 'спасибо', если он есть
    for marker in ("спасибо", "thank you", "❤️"):
        idx = piece.lower().find(marker)
        if idx != -1:
            piece = piece[:idx].strip()

    return piece


def parse_pairs(raw_text: str) -> list[tuple[str, str]]:
    """
    Универсальный парсер пачки ресурсов.
    Поддерживаем:
      - `login;password`
      - `login,password`
      - `login password`
      - `login<TAB>password`
      - строки вида: 'Логин: ... | Пароль: ... | Спасибо ...'
    """
    pairs: list[tuple[str, str]] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # 1) попытка распарсить формат с "Логин: ... | Пароль: ..."
        if "логин:" in line.lower() and "пароль:" in line.lower():
            parts = [p for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                login_part = _clean_piece(parts[0])
                pass_part = _clean_piece(parts[1])
                if login_part and pass_part:
                    pairs.append((login_part, pass_part))
                    continue

        # 2) обычные разделители ; , таб, пробел
        for sep in (";", ",", "\t", " "):
            if sep in line:
                left, right = line.split(sep, 1)
                login = _clean_piece(left)
                password = _clean_piece(right)
                if login and password:
                    pairs.append((login, password))
                break
        else:
            # если разделителей не нашли — пропускаем строку
            continue

    return pairs


# --------- ХЕНДЛЕРЫ ЗАГРУЗКИ --------- #

@router.message(F.text == "📦 Загрузить ресурсы")
async def start_upload(message: Message, state: FSMContext, role: str | None = None):
    """
    Старт загрузки из админ-меню.
    """
    if role != "admin":
        await message.answer("❌ У тебя нет прав для загрузки ресурсов.")
        return

    await state.set_state(UploadStates.CHOOSE_TYPE)
    await message.answer(
        "Выбери тип ресурса, который загружаешь:",
        reply_markup=types_keyboard(),
    )


@router.message(UploadStates.CHOOSE_TYPE)
async def choose_type(message: Message, state: FSMContext, role: str | None = None):
    """
    Выбор типа ресурса.
    """
    text = message.text.strip()

    if text == BACK_BUTTON_TEXT:
        # Назад из выбора типа — просто главное меню
        await state.clear()
        await message.answer("Главное меню:", reply_markup=manager_menu_kb())
        return

    if text not in RESOURCE_TYPES:
        await message.answer(
            "⚠️ Такой тип ресурса не знаю.\n"
            "Выбери из списка на клавиатуре.",
            reply_markup=types_keyboard(),
        )
        return

    # Сохраняем выбранный тип
    await state.update_data(res_type=text)
    await state.set_state(UploadStates.ENTER_DATA)

    await message.answer(
        "Отправь список логин:пароль, каждый с новой строки.\n\n"
        "Поддерживаем форматы:\n"
        "• <code>login;password</code>\n"
        "• <code>login,password</code>\n"
        "• <code>login password</code>\n"
        "• <code>login<TAB>password</code>\n"
        "• <code>Логин: ... | Пароль: ... | Спасибо за покупку!❤️</code>",
        reply_markup=back_keyboard(),
    )


@router.message(UploadStates.ENTER_DATA)
async def upload_data(message: Message, state: FSMContext, role: str | None = None):
    """
    Принимаем сырой текст, парсим и сохраняем ресурсы.
    """
    text = message.text

    # Назад из ввода данных — вернуться к выбору типа
    if text.strip() == BACK_BUTTON_TEXT:
        await state.set_state(UploadStates.CHOOSE_TYPE)
        await message.answer(
            "Выбери тип ресурса:",
            reply_markup=types_keyboard(),
        )
        return

    data = await state.get_data()
    res_type: str = data.get("res_type") or data.get("type") or data.get("res_type".upper(), "")

    if not res_type:
        # На всякий случай: если потеряли стейт, возвращаем в начало загрузки
        await state.set_state(UploadStates.CHOOSE_TYPE)
        await message.answer(
            "Не понял, какой тип ресурса загружаем. Выбери тип ещё раз:",
            reply_markup=types_keyboard(),
        )
        return

    pairs = parse_pairs(text)
    if not pairs:
        await message.answer(
            "❌ Не смог найти ни одной пары логин/пароль.\n"
            "Проверь формат и попробуй ещё раз.",
            reply_markup=back_keyboard(),
        )
        return

    pool = await get_pool()
    inserted = 0

    async with pool.acquire() as conn:
        for login, password in pairs:
            # Проверяем, нет ли уже такого логина этого типа
            exists = await conn.fetchrow(
                "SELECT 1 FROM resources WHERE type=$1 AND login=$2",
                res_type,
                login,
            )
            if exists:
                continue

            await conn.execute(
                """
                INSERT INTO resources (type, login, password, status)
                VALUES ($1, $2, $3, 'free')
                """,
                res_type,
                login,
                password,
            )
            inserted += 1

    await state.clear()

    await message.answer(
        "✅ Загрузка завершена.\n"
        f"Распознано пар: {len(pairs)}\n"
        f"Успешно добавлено в БД: {inserted}\n"
        f"Тип: <b>{res_type}</b>",
        reply_markup=manager_menu_kb(),
    )


# --------- УНИВЕРСАЛЬНЫЙ «НАЗАД» --------- #

@router.message(F.text == BACK_BUTTON_TEXT)
async def global_back_from_upload(
    message: Message,
    state: FSMContext,
    role: str | None = None,
):
    """
    Если по каким-то причинам пользователь нажал 'Назад' уже после
    завершения сценария загрузки (или стейт потерян) — просто
    отправляем его в нужное меню.
    """
    await state.clear()

    if role == "admin":
        # Импортируем тут, чтобы избежать циклического импорта
        from bot.handlers.admin_menu import admin_menu_kb

        await message.answer(
            "👑 Админ-меню:",
            reply_markup=admin_menu_kb(),
        )
    else:
        await message.answer(
            "Главное меню:",
            reply_markup=manager_menu_kb(),
        )
