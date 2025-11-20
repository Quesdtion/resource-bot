from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


class StatusStates(StatesGroup):
    choosing_resource = State()
    choosing_status = State()


def status_choice_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Рабочий")],
            [KeyboardButton(text="❌ Не рабочий")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@router.message(F.text == "⚙️ Статус ресурса")
async def start_status_mark(message: Message, state: FSMContext):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.GET_ISSUED_RESOURCES, message.from_user.id)

    if not rows:
        await message.answer("У тебя сейчас нет активных ресурсов для отметки статуса.")
        return

    resources = []
    text_lines = ["Выбери ресурс, которому хочешь выставить статус.\n"]
    for idx, r in enumerate(rows, start=1):
        resources.append(
            {
                "id": r["id"],
                "login": r["login"],
                "password": r["password"],
                "proxy": r["proxy"],
                "type": r["type"],
            }
        )
        line = f"{idx}) <b>{r['type']}</b> — <code>{r['login']}</code>"
        text_lines.append(line)

    await state.update_data(resources=resources)
    await state.set_state(StatusStates.choosing_resource)

    text_lines.append("\nНапиши номер ресурса (например: 1).")
    await message.answer("\n".join(text_lines), reply_markup=ReplyKeyboardRemove())


@router.message(StatusStates.choosing_resource)
async def pick_resource_index(message: Message, state: FSMContext):
    data = await state.get_data()
    resources = data.get("resources", [])

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Нужно отправить число (номер ресурса из списка). Попробуй ещё раз.")
        return

    idx = int(text)
    if idx < 1 or idx > len(resources):
        await message.answer("Неверный номер ресурса. Выбери из списка.")
        return

    chosen = resources[idx - 1]
    await state.update_data(chosen_resource=chosen)
    await state.set_state(StatusStates.choosing_status)

    msg = (
        "Выбран ресурс:\n"
        f"<b>{chosen['type']}</b> — <code>{chosen['login']}</code>\n\n"
        "Теперь выбери статус:"
    )
    await message.answer(msg, reply_markup=status_choice_kb())


@router.message(StatusStates.choosing_status)
async def apply_status(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    chosen = data.get("chosen_resource")

    if not chosen:
        await message.answer("Что-то пошло не так, попробуй начать заново: ⚙️ Статус ресурса")
        await state.clear()
        return

    resource_id = chosen["id"]
    res_type = chosen["type"]
    manager_id = message.from_user.id

    if text == "✅ Рабочий":
        mark_query = DBQueries.MARK_RESOURCE_GOOD
        action = "status_good"
        status_text = "рабочий"
    elif text == "❌ Не рабочий":
        mark_query = DBQueries.MARK_RESOURCE_BAD
        action = "status_bad"
        status_text = "НЕ рабочий"
    else:
        await message.answer("Выбери статус с клавиатуры: ✅ Рабочий или ❌ Не рабочий.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                mark_query,
                resource_id,
                manager_id,
            )

            await conn.execute(
                DBQueries.HISTORY_STATUS_CHANGE,
                resource_id,
                manager_id,
                res_type,
                action,
            )

    await state.clear()

    await message.answer(
        f"Статус ресурса <code>{chosen['login']}</code> выставлен как <b>{status_text}</b>.",
        reply_markup=ReplyKeyboardRemove(),
    )
