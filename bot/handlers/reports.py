from aiogram import Router, types
from aiogram.filters import Command

from bot.utils.queries import DBQueries

router = Router()


@router.message(Command("daily_report"))
async def daily_report(message: types.Message, role: str | None = None):
    """
    Общий отчёт за сегодня:
    - сколько ресурсов выдано
    - сколько закрыто
    - по типам
    """
    if role not in ("owner", "admin"):
        await message.answer("⛔ Эта команда доступна только администратору или владельцу.")
        return

    pool = message.bot.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.REPORT_DAILY)

    if not rows:
        await message.answer("📊 За сегодня ещё нет данных по ресурсам.")
        return

    text_lines = ["📊 <b>Общий отчёт за сегодня</b>", ""]
    total_issued = 0
    total_closed = 0

    for r in rows:
        r_type = r["type"]
        issued = r["issued"] or 0
        closed = r["closed"] or 0

        total_issued += issued
        total_closed += closed

        text_lines.append(
            f"• <b>{r_type}</b>: выдано {issued}, закрыто {closed}"
        )

    text_lines.append("\n━━━━━━━━━━━━━━")
    text_lines.append(
        f"ИТОГО: выдано <b>{total_issued}</b>, закрыто <b>{total_closed}</b>"
    )

    await message.answer("\n".join(text_lines))


@router.message(Command("manager_report"))
async def manager_report(message: types.Message, role: str | None = None):
    """
    Отчёт по менеджерам за сегодня:
    - сколько ресурсов выдал каждый
    - общее количество
    """
    if role not in ("owner", "admin"):
        await message.answer("⛔ Эта команда доступна только администратору или владельцу.")
        return

    pool = message.bot.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.REPORT_MANAGER)

    if not rows:
        await message.answer("📋 Нет данных по менеджерам за сегодня.")
        return

    text_lines = ["📋 <b>Отчёт по менеджерам за сегодня</b>", ""]
    total_all = 0

    for r in rows:
        mgr_id = r["manager_tg_id"]
        count = r["total"] or 0
        total_all += count

        text_lines.append(
            f"• <b>{mgr_id}</b>: выдал {count} ресурс(ов)"
        )

    text_lines.append("\n━━━━━━━━━━━━━━")
    text_lines.append(f"ИТОГО: всего выдано <b>{total_all}</b> ресурсов")

    await message.answer("\n".join(text_lines))


@router.message(Command("finance_report"))
async def finance_report(message: types.Message, role: str | None = None):
    """
    Финансовый отчёт за сегодня:
    - по каждому типу: количество, средняя цена, общая сумма
    - итог по всем типам
    """
    if role != "owner":
        await message.answer("⛔ Эта команда только для владельца (owner).")
        return

    pool = message.bot.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.REPORT_FINANCE)

    if not rows:
        await message.answer("💰 Нет финансовых данных за сегодня.")
        return

    text_lines = ["💰 <b>Финансовый отчёт за сегодня</b>", ""]

    total_spent_all = 0
    total_resources_all = 0

    for r in rows:
        total = r["total"] or 0
        spent = r["spent"] or 0
        avg_price = r["avg_price"] or 0.0

        total_spent_all += spent
        total_resources_all += total

        text_lines.append(
            "• <b>{type}</b>: {total} шт, ср. цена {price:.2f}₽, всего {spent:.2f}₽".format(
                type=r["type"],
                total=total,
                price=avg_price,
                spent=spent,
            )
        )

    text_lines.append("\n━━━━━━━━━━━━━━")
    text_lines.append(
        f"ИТОГО: <b>{total_resources_all}</b> шт на сумму <b>{total_spent_all:.2f}₽</b>"
    )

    await message.answer("\n".join(text_lines))
