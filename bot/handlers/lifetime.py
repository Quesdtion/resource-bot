from aiogram import Router, F, types
from bot.keyboards.lifetime_kb import lifetime_kb

router = Router()


@router.message(F.text == "⏱ Отметить срок жизни")
async def select_resource(message: types.Message):
    """
    Показывает список активных ресурсов менеджера со статусом 'issued'
    и предлагает выбрать один для отметки срока жизни.
    """
    pool = message.bot.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, type, issue_datetime FROM resources WHERE manager_tg_id=$1 AND status='issued'",
            message.from_user.id,
        )

    if not rows:
        await message.answer("❗ У вас нет активных ресурсов со статусом 'issued'.")
        return

    text_lines = ["<b>Ваши активные ресурсы:</b>"]
    kb_rows = []

    for r in rows:
        text_lines.append(f"• ID {r['id']} — {r['type']} (выдан: {r['issue_datetime']})")
        kb_rows.append([types.KeyboardButton(text=f"Ресурс {r['id']}")])

    kb = types.ReplyKeyboardMarkup(keyboard=kb_rows, resize_keyboard=True)
    await message.answer("\n".join(text_lines), reply_markup=kb)


@router.message(F.text.startswith("Ресурс "))
async def choose_lifetime(message: types.Message):
    """
    При выборе конкретного ресурса показывает инлайн-клавиатуру со сроками жизни.
    Формат текста: 'Ресурс <ID>'
    """
    try:
        res_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❗ Неверный формат. Нажмите на кнопку с ресурсом.")
        return

    await message.answer(
        f"⏱ Выберите срок жизни ресурса <b>{res_id}</b>:",
        reply_markup=lifetime_kb(res_id),
    )


@router.callback_query(F.data.startswith("lt_"))
async def process_lifetime(callback: types.CallbackQuery):
    """
    Обработка выбранного срока жизни ресурса.
    callback.data имеет формат: 'lt_<resource_id>:<minutes>'
    """
    data = callback.data.removeprefix("lt_")
    res_id_str, minutes_str = data.split(":")
    res_id = int(res_id_str)
    minutes = int(minutes_str)

    pool = callback.bot["db"]
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT * FROM resources WHERE id=$1", res_id)
        if not r:
            await callback.answer("Ресурс не найден.", show_alert=True)
            return
        if r["manager_tg_id"] != callback.from_user.id:
            await callback.answer("Это не ваш ресурс.", show_alert=True)
            return
        if r["lifetime_minutes"] is not None:
            await callback.answer("Срок жизни уже отмечен.", show_alert=True)
            return

        if minutes == -1:
            lifetime_minutes = 0
            await conn.execute(
                """
                UPDATE resources
                SET lifetime_minutes=$1,
                    end_datetime = NOW(),
                    status='dead'
                WHERE id=$2
                """,
                lifetime_minutes,
                res_id,
            )
        else:
            lifetime_minutes = minutes
            await conn.execute(
                """
                UPDATE resources
                SET lifetime_minutes=$1,
                    end_datetime = issue_datetime + ($1 || ' minutes')::interval,
                    status='dead'
                WHERE id=$2
                """,
                lifetime_minutes,
                res_id,
            )

        await conn.execute(
            """
            INSERT INTO history(resource_id, manager_tg_id, type, supplier_id, price, action, lifetime_minutes)
            VALUES ($1,$2,$3,$4,$5,'lifetime_set',$6)
            """,
            res_id,
            callback.from_user.id,
            r["type"],
            r["supplier_id"],
            r["buy_price"],
            lifetime_minutes,
        )

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        f"⏱ Срок жизни ресурса <b>{res_id}</b> отмечен: <b>{lifetime_minutes} мин</b>."
    )
    await callback.answer()
