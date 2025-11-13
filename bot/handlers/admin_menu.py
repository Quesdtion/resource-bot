from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("admin"))
async def admin_menu(message: types.Message, role: str | None = None):
    if role not in ("admin", "owner"):
        await message.answer("⛔ Нет доступа.")
        return

    await message.answer(
        "⚙ <b>Админ-меню</b>\n\n"
        "/daily_report — общий отчёт за сегодня\n"
        "/manager_report ID — отчёт по менеджеру\n"
        "/finance_report — финансовый отчёт (только owner)"
    )
