from aiogram import Router, types
from aiogram.filters import Command
from bot.utils.queries import DBQueries

router = Router()

@router.message(Command("daily_report"))
async def daily_report(message: types.Message, role: str | None = None):
    if role not in ("admin", "owner"):
        await message.answer("⛔ Недостаточно прав.")
        return

    pool = message.bot.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.REPORT_GLOBAL_TYPES)

    if not rows:
        await message.answer("Нет данных за сегодня.")
        return

    text_lines = ["📊 <b>Общий отчёт за сегодня</b>", ""]
    total_resources = 0
    total_cost = 0

    for r in rows:
        total_resources += r["total"] or 0
        total_cost += r["total_cost"] or 0
        text_lines.append(
            "🔷 <b>{type}</b>\n"
            "• Выдано: {total}\n"
            "• Рабочие: {working}\n"
            "• В блоке: {blocked}\n"
            "• Ошибки: {errors}\n"
            "• Средний срок: {lt:.1f} мин\n"
            "• Средняя цена: {price:.2f}₽\n"
            "• Расход: {cost:.2f}₽\n".format(
                type=r["type"],
                total=r["total"] or 0,
                working=r["working"] or 0,
                blocked=r["blocked"] or 0,
                errors=r["errors"] or 0,
                lt=(r["avg_lifetime"] or 0.0),
                price=(r["avg_price"] or 0.0),
                cost=(r["total_cost"] or 0.0),
            )
        )

    text_lines.append("━━━━━━━━━━━━━━")
    text_lines.append(
        f"Всего ресурсов: <b>{total_resources}</b>\nОбщий расход: <b>{total_cost:.2f}₽</b>"
    )

    await message.answer("\n".join(text_lines))

@router.message(Command("manager_report"))
async def manager_report(message: types.Message, role: str | None = None):
    if role not in ("admin", "owner"):
        await message.answer("⛔ Недостаточно прав.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат: /manager_report TG_ID_ИЛИ_ИМЯ")
        return

    target = parts[1]
    pool = message.bot.db

    async with pool.acquire() as conn:
        mgr = await conn.fetchrow(
            "SELECT * FROM managers WHERE tg_id::text=$1 OR name=$1",
            target,
        )
        if not mgr:
            await message.answer("Менеджер не найден.")
            return
        rows = await conn.fetch(DBQueries.REPORT_MANAGER, mgr["tg_id"])

    if not rows:
        await message.answer("Нет данных за сегодня по этому менеджеру.")
        return

    text_lines = [f"👤 <b>Менеджер:</b> {mgr['name']} (ID {mgr['tg_id']})", ""]
    total_resources = 0
    total_cost = 0

    for r in rows:
        total_resources += r["total"] or 0
        total_cost += r["total_cost"] or 0
        text_lines.append(
            "🔸 <b>{type}</b>\n"
            "• Выдано: {total}\n"
            "• Рабочие: {working}\n"
            "• Блоки: {blocked}\n"
            "• Средний срок: {lt:.1f} мин\n"
            "• Средняя цена: {price:.2f}₽\n"
            "• Списано: {cost:.2f}₽\n".format(
                type=r["type"],
                total=r["total"] or 0,
                working=r["working"] or 0,
                blocked=r["blocked"] or 0,
                lt=(r["avg_lifetime"] or 0.0),
                price=(r["avg_price"] or 0.0),
                cost=(r["total_cost"] or 0.0),
            )
        )

    text_lines.append("━━━━━━━━━━━━━━")
    text_lines.append(
        f"Всего ресурсов: <b>{total_resources}</b>\nОбщий расход: <b>{total_cost:.2f}₽</b>"
    )

    await message.answer("\n".join(text_lines))

@router.message(Command("finance_report"))
async def finance_report(message: types.Message, role: str | None = None):
    if role != "owner":
        await message.answer("⛔ Эта команда только для владельца (owner).")
        return

    pool = message.bot["db"]
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.REPORT_FINANCE)

    if not rows:
        await message.answer("Нет финансовых данных за сегодня.")
        return

    text_lines = ["💰 <b>Финансовый отчёт за сегодня</b>", ""]
    last_supplier = None

    for r in rows:
        if r["supplier_id"] != last_supplier:
            text_lines.append(f"🏷 Поставщик <b>{r['supplier_id']}</b>")
            last_supplier = r["supplier_id"]

        text_lines.append(
            "• {type}: {total} шт, средняя цена {price:.2f}₽, списано {spent:.2f}₽".format(
                type=r["type"],
                total=r["total"] or 0,
                price=(r["avg_price"] or 0.0),
                spent=(r["spent"] or 0.0),
            )
        )

    await message.answer("\n".join(text_lines))
