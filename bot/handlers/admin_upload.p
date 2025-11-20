from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.utils.queries import DBQueries
from bot.keyboards.admin_menu import admin_menu_kb  # если другое имя – поправь


router = Router()


class UploadStates(StatesGroup):
    enter_type = State()
    enter_price = State()
    enter_data = State()


@router.message(F.text == "📦 Загрузить ресурсы")
async def upload_start(message: Message, state: FSMContext):
    """
    Старт загрузки пачки ресурсов (кнопка в админ-меню).
    """
    await state.set_state(UploadStates.enter_type)
    await message.answer(
        "Введи тип ресурса (например: mamba, badoo, tinder).\n\n"
        "Этот тип будет установлен для всех ресурсов из этой пачки."
    )


@router.message(UploadStates.enter_type)
async def upload_set_type(message: Message, state: FSMContext):
    res_type = message.text.strip()
    if not res_type:
        await message.answer("Тип не может быть пустым, попробуй ещё раз.")
        return

    await state.update_data(type=res_type)
    await state.set_state(UploadStates.enter_price)
    await message.answer(
        "Введи цену покупки **за 1 ресурс** (числом, например: 58).\n\n"
        "Если хочешь пропустить цену – отправь 0.",
        parse_mode="Markdown"
    )


@router.message(UploadStates.enter_price)
async def upload_set_price(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    try:
        price = float(text)
    except ValueError:
        await message.answer("Не смог понять цену. Введи число, например: 58 или 58.5")
        return

    await state.update_data(price=price)
    await state.set_state(UploadStates.enter_data)

    await message.answer(
        "Теперь отправь **список ресурсов** одним сообщением.\n"
        "Каждый ресурс — **в отдельной строке**.\n\n"
        "Допустимые форматы строки:\n"
        "`login:password`\n"
        "`login:password:proxy`\n"
        "`login;password;proxy`\n"
        "`login password proxy`\n\n"
        "Пример:\n"
        "`mamba_login1:mamba_pass1:proxy1`\n"
        "`mamba_login2;mamba_pass2;proxy2`\n"
        "`mamba_login3 mamba_pass3` (без proxy)\n",
        parse_mode="Markdown"
    )


def parse_resources_block(text: str):
    """
    Разбор пачки ресурсов из произвольного текста.
    Возвращает список (login, password, proxy_or_None).
    """
    items: list[tuple[str, str, str | None]] = []

    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue

        # заменяем разные разделители на двоеточие
        for sep in [";", "|", "\t", " "]:
            raw = raw.replace(sep, ":")

        parts = [p.strip() for p in raw.split(":") if p.strip()]
        if len(parts) < 2:
            # слишком мало данных – пропускаем строку
            continue

        login = parts[0]
        password = parts[1]
        proxy = parts[2] if len(parts) >= 3 else None

        items.append((login, password, proxy))

    return items


@router.message(UploadStates.enter_data)
async def upload_save_data(message: Message, state: FSMContext):
    data = await state.get_data()
    res_type: str = data["type"]
    buy_price: float = data["price"]

    rows = parse_resources_block(message.text)
    if not rows:
        await message.answer(
            "Не смог разобрать ни одной строки. Проверь формат и попробуй снова."
        )
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
                    buy_price,
                )
                inserted += 1

    await state.clear()

    await message.answer(
        f"Готово! Добавлено ресурсов: {inserted}\n\n"
        "Они доступны для выдачи менеджерам.",
        reply_markup=admin_menu_kb()
    )
