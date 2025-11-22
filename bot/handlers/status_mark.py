from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import Command

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


# ================================
# КЛАВИАТУРЫ
# ================================

def back_only_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )


def status_choice_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🟢 Рабочий"),
                KeyboardButton(text="🔴 Нерабочий"),
            ],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True
    )


# ================================
# STATE
# ================================

class StatusFSM:
    waiting_resource_choice = "waiting_resource_choice"
    waiting_status_choice = "waiting_status_choice"


# ================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ================================

async def send_long_text(message: Message, text: str, reply_markup=None):
    """
    Безопасная отправка длинных сообщений без ошибки:
    TelegramBadRequest: message is too long
    """
    MAX = 3500
    rest = text
    first = True

    while rest:
        chunk = rest[:MAX]
        if len(rest) > MAX:
            last_n = chunk.rfind("\n")
            if last_n > 0:
                chunk = rest[:last_n]
                rest = rest[last_n + 1:]
            else:
                rest = rest[MAX:]
        else:
            rest = ""

        await message.answer(chunk, reply_markup=reply_markup if first else None)
        first = False


# ================================
# СТАРТ СТАТУСА
# ================================

@router.message(F.text == "⚙️ Статус ресурса")
async def start_status_mark(message: Message, state: FSMContext):
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.GET_RESOURCES_FOR_STATUS, message.from_user.id)

    if not rows:
        await message.answer("Нет ресурсов для смены статуса.", reply_markup=back_only_kb())
        return

    await state.update_data(rows=rows, index=0)
    await send_next_resource(message, state)


async def send_next_resource(message: Message, state: FSMContext):
    data = await state.get_data()
    rows = data["rows"]
    index = data["index"]

    if index >= len(rows):
        await message.answer("Все ресурсы обработаны.", reply_markup=back_only_kb())
        await state.clear()
        return

    r = rows[index]
    text = (
        f"<b>Ресурс {index+1} из {len(rows)}</b>\n\n"
        f"Тип: <b>{r['type']}</b>\n"
        f"Логин: <code>{r['login']}</code>\n"
        f"Пароль: <code>{r['password']}</code>\n"
    )

    await send_long_text(message, text, reply_markup=status_choice_kb())
    await state.set_state(StatusFSM.waiting_status_choice)


# ================================
# ПРИМЕНЕНИЕ СТАТУСА
# ================================

@router.message(F.text.in_({"🟢 Рабочий", "🔴 Нерабочий"}))
async def apply_status(message: Message, state: FSMContext):
    data = await state.get_data()
    rows = data["rows"]
    index = data["index"]

    if index >= len(rows):
        await message.answer("Ошибка: нет ресурса.", reply_markup=back_only_kb())
        return

    r = rows[index]

    new_status = "working" if message.text == "🟢 Рабочий" else "broken"

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            DBQueries.SET_RESOURCE_STATUS,
            new_status,
            r["id"],
        )

    # После обновления — сразу следующий ресурс
    await state.update_data(index=index + 1)
    await send_next_resource(message, state)


# ================================
# НАЗАД
# ================================

@router.message(F.text == "⬅️ Назад")
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers.manager_menu import manager_menu_kb

    await message.answer("Главное меню:", reply_markup=manager_menu_kb())
