from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


class LifetimeStates(StatesGroup):
    choosing_resource = State()
    entering_lifetime = State()


@router.message(F.text == "⏱ Отметить срок жизни")
async def start_lifetime(message: Message, state: FSMContext):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(DBQueries.GET_ISSUED_RESOURCES, message.from_user.id)

    if not rows:
        await message.answer("У тебя сейчас нет активных ресурсов для отметки времени.")
        return

    resources = []
    text_lines = ["Выбери ресурс, для которого хочешь отметить срок жизни.\n"]
    for idx, r in enumerate(rows, start=1):
        resources.append(
            {
                "id": r["id"],
                "login": r["login"],
                "type": r["type"],
            }
        )
        text_lines.append(f"{idx}) <b>{r['type']}</b> — <code>{r['login']}</code>")

    await state.update_data(resources=resources)
    await state.set_state(LifetimeStates.choosing_resource)

    text_lines.append("\nНапиши номер ресурса (например: 1).")
    await message.answer("\n".join(text_lines), reply_markup=ReplyKeyboardRemove())


@router.message(LifetimeStates.choosing_resource)
async def pick_lifetime_resource(message: Message, state: FSMContext):
    data = await state.get_data()
    resources = data.get("resources", [])

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Нужно число (номер ресурса). Попробуй ещё раз.")
        return

    idx = int(text)
    if idx < 1 or idx > len(resources):
        await message.answer("Неверный номер. Попробуй ещё раз.")
        return

    chosen = resources[idx - 1]
    await state.update_data(chosen_resource=chosen)
    await state.set_state(LifetimeStates.entering_lifetime)

    await message.answer(
        "Введи срок жизни в минутах (например: 60, 120):",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(LifetimeStates.entering_lifetime)
async def apply_lifetime(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Нужно число минут. Попробуй ещё раз.")
        return

    minutes = int(text)
    data = await state.get_data()
    chosen = data.get("chosen_resource")

    if not chosen:
        await message.answer("Ошибка состояния, начни заново: ⏱ Отметить срок жизни")
        await state.clear()
        return

    resource_id = chosen["id"]
    res_type = chosen["type"]
    manager_id = message.from_user.id

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                DBQueries.SET_LIFETIME,
                minutes,
                resource_id,
                manager_id,
            )

            await conn.execute(
                DBQueries.HISTORY_LIFETIME,
                resource_id,
                manager_id,
                res_type,
                minutes,
            )

    await state.clear()
    await message.answer(
        f"Срок жизни ресурса <code>{chosen['login']}</code> установлен: <b>{minutes}</b> минут.",
        reply_markup=ReplyKeyboardRemove(),
    )
