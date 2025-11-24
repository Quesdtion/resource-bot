from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb

router = Router()

BACK_BUTTON_TEXT = "⬅️ Назад"

# Типы ресурсов – ДОБАВЛЕН rambler
RESOURCE_TYPES = ["mamba", "tabor", "beboo", "rambler"]


def resource_type_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора типа ресурса.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t) for t in RESOURCE_TYPES],
            [KeyboardButton(text=BACK_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )


def count_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора количества (1–10) + Назад.
    """
    rows = []
    numbers = [str(i) for i in range(1, 11)]
    for i in range(0, 10, 5):
        rows.append([KeyboardButton(text=n) for n in numbers[i : i + 5]])
    rows.append([KeyboardButton(text=BACK_BUTTON_TEXT)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


class IssueStates(StatesGroup):
    waiting_type = State()
    waiting_count = State()


@router.message(F.text == "📦 Получить ресурсы")
async def start_issue(message: Message, state: FSMContext):
    """
    Первое действие – выбор типа ресурса.
    """
    await state.clear()
    await state.set_state(IssueStates.waiting_type)
    await message.answer(
        "Выбери тип ресурса, который тебе нужен:",
        reply_markup=resource_type_kb(),
    )


@router.message(IssueStates.waiting_type)
async def choose_type(message: Message, state: FSMContext):
    """
    Обработка выбранного типа ресурса.
    """
    text = message.text.strip().lower()

    if text == BACK_BUTTON_TEXT.lower():
        await state.clear()
        await message.answer("Главное меню:", reply_markup=manager_menu_kb())
        return

    if text not in RESOURCE_TYPES:
        await message.answer(
            "Выбери тип ресурса, пожалуйста, с помощью кнопки ниже.",
            reply_markup=resource_type_kb(),
        )
        return

    await state.update_data(type=text)
    await state.set_state(IssueStates.waiting_count)

    await message.answer(
        "Сколько ресурсов тебе нужно (от 1 до 10)?",
        reply_markup=count_kb(),
    )


@router.message(IssueStates.waiting_count)
async def choose_count(message: Message, state: FSMContext):
    """
    Обработка количества и фактическая выдача ресурсов.
    """
    text = message.text.strip()

    if text == BACK_BUTTON_TEXT:
        await state.set_state(IssueStates.waiting_type)
        await message.answer(
            "Окей, выбери тип ресурса ещё раз:",
            reply_markup=resource_type_kb(),
        )
        return

    if not text.isdigit():
        await message.answer(
            "Введи число от 1 до 10 или нажми кнопку.",
            reply_markup=count_kb(),
        )
        return

    count = int(text)
    if not 1 <= count <= 10:
        await message.answer(
            "Можно получить от 1 до 10 ресурсов за раз.",
            reply_markup=count_kb(),
        )
        return

    data = await state.get_data()
    r_type = data.get("type")

    if r_type not in RESOURCE_TYPES:
        await state.clear()
        await message.answer(
            "Что-то пошло не так с типом ресурса. Начни заново.",
            reply_markup=manager_menu_kb(),
        )
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, login, password, proxy, buy_price
            FROM resources
            WHERE type = $1 AND status = 'free'
            ORDER BY id
            LIMIT $2
            """,
            r_type,
            count,
        )

        if not rows:
            await state.clear()
            await message.answer(
                f"Свободных ресурсов типа {r_type} сейчас нет. "
                f"Попроси администратора загрузить новые.",
                reply_markup=manager_menu_kb(),
            )
            return

        issued_ids = [row["id"] for row in rows]

        for res_id in issued_ids:
            await conn.execute(
                """
                UPDATE resources
                SET status = 'busy',
                    manager_tg_id = $1,
                    issue_datetime = NOW(),
                    receipt_state = 'new'
                WHERE id = $2
                """,
                message.from_user.id,
                res_id,
            )

        for row in rows:
            await conn.execute(
                """
                INSERT INTO history (
                    datetime,
                    resource_id,
                    manager_tg_id,
                    type,
                    supplier_id,
                    price,
                    action,
                    receipt_state,
                    lifetime_minutes
                )
                VALUES (
                    NOW(),
                    $1,
                    $2,
                    $3,
                    NULL,
                    $4,
                    'issue',
                    'new',
                    NULL
                )
                """,
                row["id"],
                message.from_user.id,
                r_type,
                row["buy_price"],
            )

    lines = ["Готово.\nТвои ресурсы:\n"]
    for row in rows:
        login = row["login"]
        password = row["password"]
        proxy = row["proxy"]

        line = f"• <code>{login}</code> | <code>{password}</code>"
        if proxy:
            line += f" | proxy: <code>{proxy}</code>"
        lines.append(line)

    await message.answer("\n".join(lines), reply_markup=manager_menu_kb())
    await state.clear()
