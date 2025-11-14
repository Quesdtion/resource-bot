from aiogram import Router, F, types
from bot.utils.queries import DBQueries

router = Router()

# Отображаемые названия типов -> значения в базе
TYPES = {
    "Мамба": "mamba",
    "Табор": "tabor",
    "Бебо": "bebo",
}


@router.message(F.text == "📦 Получить ресурс")
async def choose_type(message: types.Message):
    """
    Показываем менеджеру выбор типа ресурса.
    """
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Мамба")],
            [types.KeyboardButton(text="Табор")],
            [types.KeyboardButton(text="Бебо")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Выбери тип ресурса:", reply_markup=kb)


@router.message(F.text.in_(list(TYPES.keys())))
async def issue_resource(message: types.Message):
    """
    Выдаём первый свободный ресурс нужного типа и логируем действие в history.
    """
    resource_type = TYPES[message.text]

    pool = message.bot.db
    async with pool.acquire() as conn:
        # Берём свободный ресурс
        resource = await conn.fetchrow(DBQueries.GET_FREE_RESOURCE, resource_type)
        if not resource:
            await message.answer("❗ Свободных ресурсов этого типа сейчас нет.")
            return

        # Помечаем ресурс выданным (ставим manager_tg_id, время, receipt_state='new')
        await conn.execute(
            DBQueries.ISSUE_RESOURCE,
            message.from_user.id,
            resource["id"],
        )

        # Пишем в историю
        await conn.execute(
            DBQueries.INSERT_HISTORY,
            resource["id"],                 # resource_id
            message.from_user.id,           # manager_tg_id
            resource["type"],               # type
            resource["supplier_id"],        # supplier_id
            resource["buy_price"],          # price
            "issue",                        # action
            resource["receipt_state"],      # receipt_state
            resource["lifetime_minutes"],   # lifetime_minutes
        )

    # Формируем текст для менеджера
    text_lines = [
        "📦 <b>Ресурс выдан</b>",
        f"ID: <b>{resource['id']}</b>",
        f"Тип: <b>{resource['type']}</b>",
        "",
    ]

    if resource.get("login"):
        text_lines.append(f"🔑 Логин: <code>{resource['login']}</code>")
    if resource.get("password"):
        text_lines.append(f"🔒 Пароль: <code>{resource['password']}</code>")
    if resource.get("proxy"):
        text_lines.append(f"🌐 Прокси: <code>{resource['proxy']}</code>")

    text = "\n".join(text_lines)
    await message.answer(text)
