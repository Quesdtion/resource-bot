# bot/handlers/upload_resources.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from db.database import get_pool
from bot.utils.queries import DBQueries
from bot.handlers.manager_menu import BACK_BUTTON_TEXT

import re

router = Router()

# Кнопки типов ресурсов (то, что видит админ)
RESOURCE_TYPE_BUTTONS = [
    "🐍 Mamba",
    "💜 Beboo",
    "🎯 Tabor",
    "❓ Другое",
]

# Маппинг "текст кнопки" -> "type" в БД
RESOURCE_TYPE_MAP = {
    "🐍 Mamba": "mamba",
    "💜 Beboo": "beboo",
    "🎯 Tabor": "tabor",
}


class UploadStates(StatesGroup):
    choosing_type = State()
    typing_custom_type = State()
    sending_data = State()


def upload_types_kb() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=btn)] for btn in RESOURCE_TYPE_BUTTONS
    ]
    keyboard.append([KeyboardButton(text=BACK_BUTTON_TEXT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def back_only_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BUTTON_TEXT)]],
        resize_keyboard=True,
    )


@router.message(F.text == "📦 Загрузить ресурсы")
async def start_upload(message: Message, role: str | None = None, state: FSMContext = None):
    """
    Вход в загрузку ресурсов из админ-меню.
    """
    if role != "admin":
        await message.answer("❌ У тебя нет доступа к загрузке ресурсов.")
        return

    await state.set_state(UploadStates.choosing_type)
    await message.answer(
        "🧩 Выбери тип ресурсов, которые хочешь загрузить:",
        reply_markup=upload_types_kb(),
    )


@router.message(UploadStates.choosing_type)
async def choose_type(message: Message, role: str | None = None, state: FSMContext = None):
    text = message.text.strip()

    if text == BACK_BUTTON_TEXT:
        # просто выходим из состояния, админ может заново открыть меню
        await state.clear()
        await message.answer("Отмена загрузки.")
        return

    if role != "admin":
        await message.answer("❌ У тебя нет доступа.")
        await state.clear()
        return

    if text == "❓ Другое":
        await state.set_state(UploadStates.typing_custom_type)
        await message.answer(
            "✏️ Введи тип ресурса текстом, например: <code>mamba</code> / <code>beboo</code> / <code>tabor</code>.",
            reply_markup=back_only_kb(),
        )
        return

    if text not in RESOURCE_TYPE_MAP:
        await message.answer("Выбери один из типов на клавиатуре или нажми Назад.")
        return

    resource_type = RESOURCE_TYPE_MAP[text]
    await state.update_data(resource_type=resource_type)
    await state.set_state(UploadStates.sending_data)

    await message.answer(
        f"✅ Тип выбран: <b>{resource_type}</b>\n\n"
        "Теперь пришли список логинов и паролей.\n"
        "Поддерживаются форматы:\n"
        "• <code>email;password</code>\n"
        "• <code>login:password</code>\n"
        "• <code>login<TAB>password</code>\n"
        "• <code>login password</code> (две части через пробел)\n"
        "• <code>email,password</code>\n"
        "• <code>Логин: xxx | Пароль: yyy ...</code>\n"
        "• <code>login: xxx password: yyy ...</code>\n\n"
        "Каждая пара — с новой строки.",
        reply_markup=back_only_kb(),
    )


@router.message(UploadStates.typing_custom_type)
async def custom_type(message: Message, role: str | None = None, state: FSMContext = None):
    text = message.text.strip()

    if text == BACK_BUTTON_TEXT:
        await state.set_state(UploadStates.choosing_type)
        await message.answer("Снова выбери тип ресурса:", reply_markup=upload_types_kb())
        return

    if role != "admin":
        await message.answer("❌ У тебя нет доступа.")
        await state.clear()
        return

    resource_type = text
    await state.update_data(resource_type=resource_type)
    await state.set_state(UploadStates.sending_data)

    await message.answer(
        f"✅ Тип выбран: <b>{resource_type}</b>\n\n"
        "Теперь пришли список логинов и паролей.\n"
        "Поддерживаемые форматы смотри выше.\n"
        "Каждая пара — с новой строки.",
        reply_markup=back_only_kb(),
    )


def parse_credentials_block(text: str) -> list[tuple[str, str]]:
    """
    Универсальный разбор пачки логин/пароль.
    Возвращает список (login, password).
    """
    pairs: list[tuple[str, str]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # 1) Формат с явным "Логин" / "Пароль" (рус/англ) и лишним текстом
        #   Примеры:
        #   - Логин: xxx | Пароль: yyy | Спасибо за покупку
        #   - login: xxx password: yyy ❤️
        m = re.search(
            r'(?i)(login|логин|user|email)\s*[:=]\s*([^|\s,]+).*?'
            r'(password|пароль|pass)\s*[:=]\s*([^|\s,]+)',
            line,
        )
        if m:
            login = m.group(2).strip()
            password = m.group(4).strip()
            if login and password:
                pairs.append((login, password))
                continue

        # Отдельный кейс: "Логин: xxx | Пароль: yyy" (как раньше)
        if "Логин:" in line and "Пароль:" in line:
            try:
                part_login = line.split("Логин:", 1)[1]
                if "|" in part_login:
                    part_login, rest = part_login.split("|", 1)
                    part_pwd = rest.split("Пароль:", 1)[1]
                else:
                    pieces = part_login.split("Пароль:", 1)
                    part_login = pieces[0]
                    part_pwd = pieces[1] if len(pieces) > 1 else ""
                login = part_login.strip(" |:")
                password = part_pwd.strip(" |:")
                if login and password:
                    pairs.append((login, password))
                    continue
            except Exception:
                pass  # если не вышло — пробуем другие варианты

        # 2) Вариант: "login;password"
        if ";" in line:
            left, right = line.split(";", 1)
            login = left.strip()
            password = right.strip()
            if login and password:
                pairs.append((login, password))
                continue

        # 3) Вариант: "login<TAB>password"
        if "\t" in line:
            left, right = line.split("\t", 1)
            login = left.strip()
            password = right.strip()
            if login and password:
                pairs.append((login, password))
                continue

        # 4) Вариант: CSV "email,password"
        if "," in line:
            left, right = line.split(",", 1)
            login = left.strip()
            password = right.strip()
            if login and password:
                pairs.append((login, password))
                continue

        # 5) Вариант: "login:password"
        # (но НЕ путать с "login: xxx password: yyy" — он выше уже обработан)
        if ":" in line:
            left, right = line.split(":", 1)
            login = left.strip()
            password = right.strip()
            if login and password and " " not in login:
                # если в login уже пробелы — вероятно это был формат с лишним текстом
                pairs.append((login, password))
                continue

        # 6) Вариант: "login password" — ровно две части через пробел
        parts = line.split()
        if len(parts) == 2:
            login, password = parts[0].strip(), parts[1].strip()
            if login and password:
                pairs.append((login, password))
                continue

        # Если ничего не подошло — пропускаем строку
        continue

    return pairs


@router.message(UploadStates.sending_data)
async def receive_data(message: Message, role: str | None = None, state: FSMContext = None):
    text = message.text

    if text.strip() == BACK_BUTTON_TEXT:
        await state.set_state(UploadStates.choosing_type)
        await message.answer("Загрузка отменена. Снова выбери тип ресурса:", reply_markup=upload_types_kb())
        return

    if role != "admin":
        await message.answer("❌ У тебя нет доступа.")
        await state.clear()
        return

    data = await state.get_data()
    resource_type = data.get("resource_type")

    if not resource_type:
        await message.answer("Ошибка: не выбран тип ресурса. Попробуй начать заново.")
        await state.clear()
        return

    pairs = parse_credentials_block(text)
    if not pairs:
        await message.answer(
            "Не удалось распознать ни одного логина/пароля.\n"
            "Проверь формат и попробуй ещё раз.",
            reply_markup=back_only_kb(),
        )
        return

    pool = await get_pool()
    inserted = 0

    async with pool.acquire() as conn:
        for login, password in pairs:
            try:
                await conn.execute(
                    DBQueries.INSERT_RESOURCE_BULK,
                    resource_type,
                    login,
                    password,
                    None,     # proxy
                    None,     # buy_price
                )
                inserted += 1
            except Exception:
                # Если конкретный логин не вставился — просто пропустим
                continue

    await state.clear()

    await message.answer(
        f"✅ Загрузка завершена.\n"
        f"Распознано пар: <b>{len(pairs)}</b>\n"
        f"Успешно добавлено в БД: <b>{inserted}</b>\n\n"
        f"Тип: <b>{resource_type}</b>",
    )
