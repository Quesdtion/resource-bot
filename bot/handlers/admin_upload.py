from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.utils.queries import DBQueries
from bot.handlers.admin_menu import admin_menu_kb

router = Router()


class UploadStates(StatesGroup):
    enter_type = State()
    enter_data = State()


async def _is_admin(user_id: int) -> bool:
    """
    Проверяем роль пользователя в таблице managers.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.CHECK_MANAGER_ROLE, user_id)

    return bool(row and row["role"] == "admin")


@router.message(F.text == "📦 Загрузить ресурсы")
async def upload_start(message: Message, state: FSMContext):
    """
    Старт диалога загрузки ресурсов.
    """
    if not await _is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return

    await state.set_state(UploadStates.enter_type)
    await message.answer(
        "Введи тип ресурса (например: mamba, tabor, bebo).\n\n"
        "Этот тип будет установлен для всех ресурсов из этой пачки."
    )


@router.message(UploadStates.enter_type)
async def upload_set_type(message: Message, state: FSMContext):
    res_type = message.text.strip()
    if not res_type:
        await message.answer("Тип не может быть пустым, введи снова.")
        return

    await state.update_data(res_type=res_type)
    await state.set_state(UploadStates.enter_data)

    await message.answer(
        "Теперь отправь **пачку аккаунтов** одним сообщением.\n"
        "Каждый аккаунт — с новой строки.\n\n"
        "Поддерживаемые форматы строки:\n"
        "- `логин;пароль`\n"
        "- `логин пароль` (через пробел или TAB)\n"
        "- `логин:пароль`\n"
        "- `логин:пароль:прокси`\n"
        "- `Логин: XXX | Пароль: YYY | ...`\n\n"
        "Примеры:\n"
        "`email@mail.com;pass123`\n"
        "`email@mail.com\tpass123`\n"
        "`79261234567:qwe123`\n"
        "`login:pass:proxy:port`\n"
        "`Логин: mail@mail.com | Пароль: Pass123 | Спасибо за покупку!❤️`\n",
        parse_mode="Markdown"
    )


def parse_line(line: str):
    """
    Универсальный парсер одной строки.
    Возвращает (login, password, proxy) или None, если строка нераспознаваема.
    """

    original = line
    line = line.strip()
    if not line:
        return None

    # 1) Формат "Логин: XXX | Пароль: YYY | ..."
    if "Логин:" in line and "Пароль:" in line:
        try:
            # Логин
            after_login = line.split("Логин:", 1)[1]
            login_part = after_login.split("|", 1)[0].strip()

            # Пароль
            after_pass = line.split("Пароль:", 1)[1]
            pass_part = after_pass.split("|", 1)[0].strip()

            login = login_part
            password = pass_part
            proxy = None

            if login and password:
                return login, password, proxy
        except Exception:
            # Если вдруг не смогли распарсить — идём дальше
            pass

    # 2) Формат с двоеточиями "login:pass" или "login:pass:proxy"
    if ":" in line and "Логин:" not in line:
        parts = [p.strip() for p in line.split(":") if p.strip()]
        if len(parts) >= 2:
            login = parts[0]
            password = parts[1]
            proxy = parts[2] if len(parts) >= 3 else None
            if login and password:
                return login, password, proxy

    # 3) Остальные: ; | TAB | пробелы
    for sep in ["\t", ";", "|"]:
        line = line.replace(sep, " ")

    # Замена многократных пробелов на один
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
    Разбор целого блока текста (много строк).
    Возвращает:
      - список кортежей (login, password, proxy_or_None)
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


@router.message(UploadStates.enter_data)
async def upload_save_data(message: Message, state: FSMContext):
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
                    res_type,      # type
                    login,
                    password,
                    proxy,
                    0,             # buy_price (сейчас 0, при желании можно добавить шаг ввода цены)
                )
                inserted += 1

    await state.clear()

    text = (
        f"✅ Загрузка завершена.\n\n"
        f"Тип ресурса: <b>{res_type}</b>\n"
        f"Добавлено в базу: <b>{inserted}</b>\n"
    )
    if skipped:
        text += f"Пропущено строк (не распознаны): <b>{skipped}</b>"

    await message.answer(text, reply_markup=admin_menu_kb())
