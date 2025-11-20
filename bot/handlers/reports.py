from aiogram import Router, F
from aiogram.types import Message

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


@router.message(F.text == "📊 Отчёт по ресурсам")
async def report_resources(message: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.REPORT_RESOURCES)

    if not row or row["total"] is None or row["total"] == 0:
        await message.answer("ℹ️ В базе пока нет ресурсов.")
        return

    text = (
        "📊 <b>Отчёт по ресурсам за сегодня</b>\n\n"
        f"Всего ресурсов: <b>{row['total']}</b>\n"
        f"Свободно: <b>{row['free']}</b>\n"
        f"В работе: <b>{row['busy']}</b>\n"
        f"Использовано сегодня: <b>{row['expired_today']}</b>\n"
        f"Выдано сегодня: <b>{row['issued_today']}</b>\n"
    )

    await message.answer(text)


@router.message(F.text == "💰 Финансовый отчёт")
async def report_finance(message: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.REPORT_FINANCE)

    total = row["total_purchase_cost"] if row and row["total_purchase_cost"] is not None else 0

    if total == 0:
        await message.answer("💰 За сегодня ещё не было учтённых покупок ресурсов.")
        return

    text = (
        "💰 <b>Финансовый отчёт за сегодня</b>\n\n"
        f"Всего потрачено на закупку ресурсов: <b>{total}</b>\n"
    )

    await message.answer(text)
