from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.utils.queries import DBQueries
from bot.handlers.admin_menu import admin_menu_kb

router = Router()


# Типы ресурсов для кнопок при загрузке
RESOURCE_TYPES = ["mamba", "tabor", "bebo"]


class UploadStates(StatesGroup):
    choosing_type = State()
    entering_data = State()


async def _is_admin(user_id: int) -> bool:
    """
    Проверяем, что пользователь — админ (role='admin' в таблице managers).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.CHECK_MANAGER_ROLE, user_id)

    return bool(row and row["role"] == "admin")


def resource_type_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора типа ресурса при загрузке.
    """
    buttons = [[KeyboardButton(text=t)] for t in RESOURCE_TYPES]
    buttons.append([KeyboardButton(text="Другое")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@router.message(F.text == "📦 Загрузить ресурсы")
async def upload_start(message: Message, state: FSMContext):
    """
    Старт диалога загрузки ресурсов.
    """
    if not await _is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return

    await state.set_state(UploadStates.choosing_type)
    await message.answer(
        "Выбери тип ресурса для загрузки:",
        reply_markup=resource_type_kb(),
    )


@router.message(UploadStates.choosing_type)
async def set_upload_type(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == "Другое":
        await message.answer(
            "Введи тип ресурса вручную (например: mamba_email, phone, vk и т.п.):",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Остаёмся в том же состоянии, ждём текста
        return

    # Если нажата готовая кнопка или введён свой тип
    res_type = text.lower()

    if res_type == "":
        await message.answer("Тип не может быть пустым. Введи тип ещё раз.")
        return

    await state.update_data(res_type=res_type)
    await state.set_state(UploadStates.entering_data)

    await message.answer(
        "Теперь отправь <b>пачку аккаунтов</b> одним сообщением.\n"
        "Каждый аккаунт — с новой строки.\n\n"
        "Поддерживаемые форматы строки:\n"
        "- <code>логин;пароль</code>\n"
        "- <code>логин пароль</code> (TAB или пробел)\n"
        "- <code>логин:пароль</code>\n"
        "- <code>логин:пароль:прокси</code>\n"
        "- <code>Логин: XXX | Пароль: YYY | ...</code>\n\n"
        "Примеры:\n"
        "<code>email@mail.com;pass123</code>\n"
        "<code>email@mail.com\tpass123</code>\n"
        "<code>79261234567:qwe123</code>\n"
        "<code>login:pass:proxy:port</code>\n"
        "<code>Логин: mail@mail.com | Пароль: Pass123 | Спасибо за покупку!❤️</code>\n",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


def parse_line(line: str):
    """
    Универсальный парсер одной строки.
    Возвращает (login, password, proxy) или None.
    """
    line = line.strip()
    if not line:
        return None

    # 1) Формат "Логин: XXX | Пароль: YYY | ..."
    if "Логин:" in line and "Пароль:" in line:
        try:
            after_login = line.split("Логин:", 1)[1]
            login_part = after_login.split("|", 1)[0].strip()

            after_pass = line.split("Пароль:", 1)[1]
            pass_part = after_pass.split("|", 1)[0].strip()

            login = login_part
            password = pass_part
            proxy = None

            if login and password:
                return login, password, proxy
        except Exception:
            pass  # Пойдём дальше по другим форматам

    # 2) Формат с двоеточиями: login:pass или login:pass:proxy
    if ":" in line and "Логин:" not in line:
        parts = [p.strip() for p in line.split(":") if p.strip()]
        if len(parts) >= 2:
            login = parts[0]
            password = parts[1]
            proxy = parts[2] if len(parts) >= 3 else None
            if login and password:
                return login, password, proxy

    # 3) Остальное: ; | TAB | пробелы
    for sep in ["\t", ";", "|"]:
        line = line.replace(sep, " ")

    parts = [p.strip() for p in line.split(" ") if p.strip()]
    if len(parts) < 2:
        return None

    login = parts[0]
    password = parts[1]
    proxy = parts[2] if len(parts) >= 3 else None

    if not login or not password:
        return None

    return login, password, proxy


def parse_block(text: str):
    """
    Разбор блока текста на множество строк.
    Возвращает:
      - список (login, password, proxy_or_None)
      - количество пропущенных строк
    """
    parsed = []
    skipped = 0

    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue

        result = parse_line(raw)
        if result is None:
            skipped += 1
            continue

        parsed.append(result)

    return parsed, skipped


@router.message(UploadStates.entering_data)
async def save_uploaded_resources(message: Message, state: FSMContext):
    data = await state.get_data()
    res_type = data["res_type"]

    rows, skipped = parse_block(message.text)

    if not rows:
        await message.answer("Не смог разобрать ни одной строки. Проверь формат.")
        await state.clear()
        return

    pool = await get_pool()
    inserted = 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            for login, password, proxy in rows:
                await conn.execute(
                    DBQueries.INSERT_RESOURCE_BULK,
                    res_type,
                    login,
                    password,
                    proxy,
                    0,  # buy_price = 0, при желании потом добавим шаг с ценой
                )
                inserted += 1

    await state.clear()

    text = (
        "✅ Загрузка завершена.\n\n"
        f"Тип ресурса: <b>{res_type}</b>\n"
        f"Добавлено в базу: <b>{inserted}</b>\n"
    )
    if skipped:
        text += f"Пропущено строк (не распознаны): <b>{skipped}</b>"

    await message.answer(text, reply_markup=admin_menu_kb())
