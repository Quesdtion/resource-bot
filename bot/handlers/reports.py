# bot/handlers/reports.py

from aiogram import Router, F
from aiogram.types import Message

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


# 📊 Отчёт по ресурсам
@router.message(F.text == "📊 Отчёт по ресурсам")
async def report_resources(message: Message) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.REPORT_RESOURCES)

    if not row:
        await message.answer("За сегодня данных по ресурсам нет.")
        return

    text = (
        "📊 Отчёт по ресурсам за сегодня\n"
        f"Всего ресурсов: {row['total']}\n"
        f"Свободно: {row['free']}\n"
        f"В работе: {row['busy']}\n"
        f"Просрочено: {row['expired']}\n"
        f"Выдано сегодня: {row['issued_today']}"
    )

    await message.answer(text)


# 💰 Финансовый отчёт
@router.message(F.text == "💰 Финансовый отчёт")
async def report_finance(message: Message) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(DBQueries.REPORT_FINANCE)

    if not row or row["total_spent"] is None:
        await message.answer("За сегодня финансовых данных нет.")
        return

    text = (
        "💰 Финансовый отчёт за сегодня\n"
        f"Куплено ресурсов: {row['resources_bought']} шт.\n"
        f"Потрачено на закупку: {row['total_spent']} у.е.\n"
        f"Средняя цена за ресурс: {row['avg_price']:.2f} у.е."
    )

    await message.answer(text)
