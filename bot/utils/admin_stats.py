# bot/utils/admin_stats.py

from aiogram.types import Message

from db.database import get_pool


async def send_free_resources_stats(message: Message) -> None:
    """
    Отправляет админу статистику по свободным ресурсам:
    сколько свободных ресурсов каждого типа сейчас есть в БД.
    Вызываем ТОЛЬКО для админов.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT type, COUNT(*) AS cnt
            FROM resources
            WHERE status = 'free'
              AND manager_tg_id IS NULL
            GROUP BY type
            ORDER BY type
            """
        )

    if not rows:
        text = "📊 Сейчас нет свободных ресурсов."
    else:
        lines = ["📊 Свободные ресурсы сейчас:\n"]
        for r in rows:
            r_type = r["type"]
            cnt = r["cnt"]
            lines.append(f"• {r_type} — {cnt} шт.")
        text = "\n".join(lines)

    await message.answer(text)
