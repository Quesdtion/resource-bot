from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb
from bot.utils.admin_stats import send_free_resources_stats

import re

router = Router()

BACK_BUTTON = "⬅️ Назад"

# Список типов, которые можно загружать
RESOURCE_TYPES = [
    "mamba",
    "tabor",
    "beboo",
    "rambler",
    "mamba [dolphin]",
]


def resource_types_kb() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []

    for idx, t in enumerate(RESOURCE_TYPES, start=1):
        row.append(KeyboardButton(text=t))
        if idx % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([KeyboardButton(text=BACK_BUTTON)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def back_only_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BUTTON)]],
        resize_keyboard=True,
    )


class UploadStates(StatesGroup):
    waiting_type = State()
    waiting_text = State()


# ==========================
# Старт загрузки
# ==========================

@router.message(F.text == "📦 Загрузить ресурсы")
async def upload_start(message: Message, state: FSMContext):
    await state.set_state(UploadStates.waiting_type)
    await message.answer("Выбери тип ресурса:", reply_markup=resource_types_kb())


@router.message(F.text == BACK_BUTTON)
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=manager_menu_kb())


# ==========================
# Выбор типа ресурса
# ==========================

@router.message(UploadStates.waiting_type)
async def choose_type(message: Message, state: FSMContext):
    r_type = (message.text or "").strip()

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
        "• email<TAB>password\n"
        "• строки вида «Логин: xxx | Пароль: yyy | …»\n"
        "• строки с лишним текстом — найдём автоматически\n\n"
        "Для типа <b>mamba [dolphin]</b> достаточно списка имён профилей "
        "в формате:\n"
        "  - dam8134\n"
        "  - tab2601\n"
        "  - fad4756\n",
        reply_markup=back_only_kb(),
    )


# ==========================
# Парсер строки login / password
# ==========================

def parse_login_password(line: str) -> tuple[str, str] | None:
    """
    Универсальный парсер строки:
    - режет по табам, ; , : |
    - понимает "Логин: ... | Пароль: ..."
    - понимает просто "login password"
    Возвращает (login, password) или None.
    """
    line = line.strip()
    if not line:
        return None

    # Убираем маркеры списков "- "
    if line.startswith("-"):
        line = line[1:].strip()

    if not line:
        return None

    lower = line.lower()

    # 1) Формат с подписями: "Логин: xxx | Пароль: yyy | ..."
    if ("логин" in lower or "login" in lower) and ("парол" in lower or "pass" in lower):
        # Ищем логин
        m_login = re.search(
            r"(логин|login)\s*[:\-]?\s*([^\s|,;:]+)", line, flags=re.IGNORECASE
        )
        # Ищем пароль
        m_pass = re.search(
            r"(пароль|parol|pass)\s*[:\-]?\s*([^\s|,;:]+)", line, flags=re.IGNORECASE
        )
        if m_login and m_pass:
            return m_login.group(2), m_pass.group(2)

    # 2) Простые разделители: таб, ; , : |
    for sep in ["\t", ";", ",", ":", "|"]:
        if sep in line:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]

    # 3) Пробелы
    parts = line.split()
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()

    return None


# ==========================
# Обработка текста загрузки
# ==========================

@router.message(UploadStates.waiting_text)
async def process_upload_text(message: Message, state: FSMContext, role: str | None = None):
    if message.text == BACK_BUTTON:
        return await back_to_menu(message, state)

    data = await state.get_data()
    r_type: str = data.get("type")  # тип, выбранный админом

    lines = message.text.splitlines()
    parsed: list[tuple[str, str]] = []

    # Особый случай: mamba [dolphin] — только имя профиля
    if r_type == "mamba [dolphin]":
        for ln in lines:
            s = (ln or "").strip()
            if not s:
                continue
            if s.startswith("-"):
                s = s[1:].strip()
            if not s:
                continue
            login = s
            password = ""  # пароля нет, храним пустую строку
            parsed.append((login, password))
    else:
        # Обычные ресурсы — парсим логин/пароль
        for ln in lines:
            res = parse_login_password(ln)
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
                # дубликат или другая ошибка — пропускаем
                pass

    text = (
        f"✅ Загрузка завершена.\n"
        f"Распознано строк: {total}\n"
        f"Успешно добавлено в БД: {added}\n\n"
        f"Тип: {r_type}"
    )

    await message.answer(text, reply_markup=manager_menu_kb())
    await state.clear()

    # После каждой загрузки — статистика свободных ресурсов (только админу)
    if role == "admin":
        await send_free_resources_stats(message)
