from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.admin_menu import admin_menu_kb
from bot.handlers.manager_menu import BACK_BUTTON_TEXT
from bot.utils.queries import DBQueries

router = Router()


class ReportsStates(StatesGroup):
    choosing_period = State()


def reports_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 За сегодня")],
            [KeyboardButton(text="📊 За 7 дней")],
            [KeyboardButton(text=BACK_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == "📊 Отчёты")
async def reports_entry(message: Message, role: str | None = None, state: FSMContext = None):
    """
    Вход в меню отчётов (только для админов).
    """
    if role != "admin":
        await message.answer("❌ У тебя нет доступа к отчётам.")
        return

    await state.set_state(ReportsStates.choosing_period)
    await message.answer(
        "📊 Отчёты.\nВыбери период:",
        reply_markup=reports_menu_kb(),
    )


@router.message(ReportsStates.choosing_period)
async def choose_period(message: Message, role: str | None = None, state: FSMContext = None):
    text = message.text.strip()

    if text == BACK_BUTTON_TEXT:
        await state.clear()
        await message.answer("Возвращаю в админ-меню:", reply_markup=admin_menu_kb())
        return

    if role != "admin":
        await message.answer("❌ У тебя нет доступа к отчётам.")
        await state.clear()
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        if text == "📊 За сегодня":
            # Итого по ресурсам за сегодня (готовый SQL из DBQueries)
            res_row = await conn.fetchrow(DBQueries.REPORT_RESOURCES)
            fin_row = await conn.fetchrow(DBQueries.REPORT_FINANCE)

            total = res_row["total"] if res_row and res_row["total"] is not None else 0
            free = res_row["free"] if res_row and res_row["free"] is not None else 0
            busy = res_row["busy"] if res_row and res_row["busy"] is not None else 0
            expired_today = res_row["expired_today"] if res_row and res_row["expired_today"] is not None else 0
            issued_today = res_row["issued_today"] if res_row and res_row["issued_today"] is not None else 0

            total_purchase_cost = (
                fin_row["total_purchase_cost"] if fin_row and fin_row["total_purchase_cost"] is not None else 0
            )

            text_report = (
                "📊 Отчёт за <b>сегодня</b>:\n\n"
                f"Всего ресурсов в системе: <b>{total}</b>\n"
                f"Свободных: <b>{free}</b>\n"
                f"Выданных: <b>{busy}</b>\n"
                f"Просрочено сегодня (lifetime): <b>{expired_today}</b>\n"
                f"Выдано сегодня: <b>{issued_today}</b>\n\n"
                f"💰 Закупка за сегодня: <b>{total_purchase_cost}</b>\n"
            )

            await message.answer(text_report, reply_markup=reports_menu_kb())
            return

        elif text == "📊 За 7 дней":
            # Более "сырой" отчёт по истории за неделю
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN action = 'purchase' THEN price ELSE 0 END), 0) AS purchases_sum,
                    COALESCE(COUNT(*) FILTER (WHERE action = 'purchase'), 0) AS purchases_count,
                    COALESCE(COUNT(*) FILTER (WHERE action = 'issued'), 0) AS issued_count,
                    COALESCE(COUNT(*) FILTER (WHERE action = 'status_good'), 0) AS good_count,
                    COALESCE(COUNT(*) FILTER (WHERE action = 'status_bad'), 0) AS bad_count
                FROM history
                WHERE datetime >= NOW() - INTERVAL '7 days';
                """
            )

            text_report = (
                "📊 Отчёт за <b>последние 7 дней</b>:\n\n"
                f"Закупок (шт): <b>{row['purchases_count']}</b>\n"
                f"Сумма закупки: <b>{row['purchases_sum']}</b>\n\n"
                f"Выдач ресурсов (issued): <b>{row['issued_count']}</b>\n"
                f"Отмечено рабочих (status_good): <b>{row['good_count']}</b>\n"
                f"Отмечено нерабочих (status_bad): <b>{row['bad_count']}</b>\n"
            )

            await message.answer(text_report, reply_markup=reports_menu_kb())
            return

        else:
            await message.answer("Выбери один из вариантов на клавиатуре.")
            return
