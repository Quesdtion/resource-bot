from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.utils.queries import DBQueries

router = Router()


class IssueStates(StatesGroup):
    choosing_type = State()
    choosing_quantity = State()


def quantity_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура с выбором количества 1–10.
    """
    row1 = [KeyboardButton(text=str(i)) for i in range(1, 6)]
    row2 = [KeyboardButton(text=str(i)) for i in range(6, 11)]
    return ReplyKeyboardMarkup(
        keyboard=[row1, row2],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@router.message(F.text == "📦 Получить ресурсы")
async def start_issue(message: Message, state: FSMContext):
    """
    Старт диалога выдачи ресурсов менеджеру.
    """
    await state.set_state(IssueStates.choosing_type)
    await message.answer(
        "Введи тип ресурса, который тебе нужен (например: mamba, tabor, bebo)."
    )


@router.message(IssueStates.choosing_type)
async def set_type(message: Message, state: FSMContext):
    res_type = message.text.strip().lower()
    if not res_type:
        await message.answer("Тип не может быть пустым. Введи тип ресурса ещё раз.")
        return

    await state.update_data(res_type=res_type)
    await state.set_state(IssueStates.choosing_quantity)

    await message.answer(
        "Сколько ресурсов тебе нужно (от 1 до 10)?",
        reply_markup=quantity_kb(),
    )


@router.message(IssueStates.choosing_quantity)
async def issue_resources(message: Message, state: FSMContext):
    text = message.text.strip()

    if not text.isdigit():
        await message.answer("Нужно число от 1 до 10. Выбери на клавиатуре.")
        return

    qty = int(text)
    if qty < 1 or qty > 10:
        await message.answer("Можно запросить от 1 до 10 ресурсов.")
        return

    data = await state.get_data()
    res_type = data["res_type"]
    manager_id = message.from_user.id

    pool = await get_pool()
    issued = []

    async with pool.acquire() as conn:
        async with conn.transaction():
            for _ in range(qty):
                # Берём свободный ресурс нужного типа
                resource = await conn.fetchrow(
                    DBQueries.GET_FREE_RESOURCE_BY_TYPE,
                    res_type,
                )
                if not resource:
                    break

                # Обновляем статус ресурса
                await conn.execute(
                    DBQueries.ISSUE_RESOURCE,
                    manager_id,
                    resource["id"],
                )

                # Логируем выдачу
                await conn.execute(
                    DBQueries.HISTORY_LOG,
                    resource["id"],
                    manager_id,
                    res_type,
                )

                issued.append(resource)

    await state.clear()

    await message.answer(
        "Готово.",
        reply_markup=ReplyKeyboardRemove(),
    )

    if not issued:
        await message.answer(
            f"Свободных ресурсов типа <b>{res_type}</b> сейчас нет. "
            f"Попроси администратора загрузить новые."
        )
        return

    lines = [
        f"📦 Выдано ресурсов: <b>{len(issued)}</b> (тип: <b>{res_type}</b>)\n"
    ]
    for idx, r in enumerate(issued, start=1):
        login = r["login"]
        password = r["password"]
        proxy = r["proxy"]

        line = f"{idx}) <code>{login}</code> | <code>{password}</code>"
        if proxy:
            line += f" | proxy: <code>{proxy}</code>"

        lines.append(line)

    await message.answer("\n".join(lines))
