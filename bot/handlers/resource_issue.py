from aiogram import Router, F, types
from bot.utils.queries import DBQueries
from bot.keyboards.resource_kb import receipt_state_kb

router = Router()

# Кнопка в меню менеджера: "📦 Получить ресурс"
@router.message(F.text == "📦 Получить ресурс")
async def choose_type(message: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Мамба")],
            [types.KeyboardButton(text="Табор")],
            [types.KeyboardButton(text="Бебо")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Выберите тип ресурса:", reply_markup=kb)


TYPES = {
    "Мамба": "mamba",
    "Табор": "tabor",
    "Бебо": "bebo",
}

@router.message(F.text.in_(list(TYPES.keys())))
async def issue_resource(message: types.Message):
    resource_type = TYPES[message.text]
    # пул БД берём из bot.db, как мы настроили в main.py
    pool = message.bot.db

    async with pool.acquire() as conn:
        resource = await conn.fetchrow(DBQueries.GET_FREE_RESOURCE, resource_type)
        if not resource:
            await message.answer("❗ Свободных ресурсов этого типа нет.")
            return

        # помечаем ресурс как выданный
        await conn.execute(DBQueries.ISSUE_RESOURCE, message.from_user.id, resource["id"])
        # пишем в историю
        await conn.execute(
            DBQueries.HISTORY_LOG,
            resource["id"],
            message.from_user.id,
            resource["type"],
            resource["supplier_id"],
            resource["buy_price"],
            "issued",
            None,
            None,
        )

    text = (
        "📦 <b>Ресурс выдан</b>\n\n"
        f"ID: <b>{resource['id']}</b>\n"
        f"Тип: <b>{resource['type']}</b>\n\n"
        f"Логин: <code>{resource['login']}</code>\n"
        f"Пароль: <code>{resource['password']}</code>\n"
        f"Прокси: <code>{resource['proxy'] or 'нет'}</code>\n\n"
        f"Поставщик: <b>{resource['supplier_id']}</b>\n"
        f"Закупочная цена: <b>{resource['buy_price']}₽</b>\n\n"
        "Отметь состояние ресурса кнопками ниже 👇"
    )
    await message.answer(text, reply_markup=receipt_state_kb(resource["id"]))


@router.callback_query(F.data.startswith("rcpt_"))
async def receipt_state_handler(callback: types.CallbackQuery):
    action, res_id_str = callback.data.split(":")
    res_id = int(res_id_str)
    pool = callback.bot.db

    if action == "rcpt_working":
        status = "issued"
        receipt = "working"
        msg = "🟢 Ресурс отмечен как рабочий."
    elif action == "rcpt_blocked":
        status = "blocked_at_receipt"
        receipt = "blocked"
        msg = "🔴 Ресурс отмечен как в блоке при получении."
    else:
        status = "error_on_login"
        receipt = "error"
        msg = "⚠️ Отмечена ошибка входа."

    async with pool.acquire() as conn:
        await conn.execute(DBQueries.SET_RECEIPT_STATE, receipt, status, res_id)
        r = await conn.fetchrow("SELECT * FROM resources WHERE id=$1", res_id)
        await conn.execute(
            DBQueries.HISTORY_LOG,
            res_id,
            callback.from_user.id,
            r["type"],
            r["supplier_id"],
            r["buy_price"],
            "receipt_status",
            receipt,
            None,
        )

    await callback.message.edit_reply_markup()
    await callback.message.answer(msg)
    await callback.answer()
