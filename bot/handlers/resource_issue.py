# bot/handlers/resource_issue.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb

router = Router()

# ---------------------------------------------------
# Константы и клавиатуры
# ---------------------------------------------------

BACK_BUTTON = "⬅️ Назад"

RESOURCE_TYPES = ["mamba", "tabor", "beboo", "rambler"]


def issue_types_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора типа ресурса при выдаче.
    """
    row = [KeyboardButton(text=t) for t in RESOURCE_TYPES]
    return ReplyKeyboardMarkup(
        keyboard=[row, [KeyboardButton(text=BACK_BUTTON)]],
        resize_keyboard=True,
    )


def count_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора количества (1–10) + Назад.
    """
    keyboard = []
    nums = [str(i) for i in range(1, 11)]
    # 5 кнопок в строке
    for i in range(0, 10, 5):
        keyboard.append([KeyboardButton(text=n) for n in nums[i : i + 5]])
    keyboard.append([KeyboardButton(text=BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# ---------------------------------------------------
# FSM
# ---------------------------------------------------

class IssueStates(StatesGroup):
    choosing_type = State()
    choosing_count = State()


# ---------------------------------------------------
# Старт выдачи
# ---------------------------------------------------

@router.message(F.text == "📦 Получить ресурсы")
async def issue_start(message: Message, state: FSMContext):
    await state.set_state(IssueStates.choosing_type)
    await message.answer(
        "Выбери тип ресурса, который тебе нужен:",
        reply_markup=issue_types_kb(),
    )


# ---------------------------------------------------
# Обработка «Назад»
# ---------------------------------------------------

@router.message(IssueStates.choosing_type, F.text == BACK_BUTTON)
async def back_from_type(message: Message, state: FSMContext):
    # Из выбора типа — сразу в главное меню
    await state.clear()
    await message.answer("Главное меню:", reply_markup=manager_menu_kb())


@router.message(IssueStates.choosing_count, F.text == BACK_BUTTON)
async def back_from_count(message: Message, state: FSMContext):
    # Из выбора количества — назад к выбору типа
    await state.set_state(IssueStates.choosing_type)
    await message.answer("Снова выбери тип ресурса:", reply_markup=issue_types_kb())


# ---------------------------------------------------
# Выбор типа
# ---------------------------------------------------

@router.message(IssueStates.choosing_type)
async def choose_type(message: Message, state: FSMContext):
    r_type = (message.text or "").strip().lower()

    if r_type not in RESOURCE_TYPES:
        await message.answer(
            "Выбери тип ресурса кнопкой снизу 👇",
            reply_markup=issue_types_kb(),
        )
        return

    await state.update_data(type=r_type)
    await state.set_state(IssueStates.choosing_count)
    await message.answer(
        "Сколько ресурсов тебе нужно (от 1 до 10)?",
        reply_markup=count_kb(),
    )


# ---------------------------------------------------
# Выбор количества и выдача
# ---------------------------------------------------

@router.message(IssueStates.choosing_count)
async def choose_count(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    # Защита от мусора
    if not text.isdigit():
        await message.answer("Нажми число на клавиатуре от 1 до 10 🙂")
        return

    count = int(text)
    if not 1 <= count <= 10:
        await message.answer("Нужно число от 1 до 10.")
        return

    data = await state.get_data()
    r_type = data.get("type")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Берём свободные ресурсы нужного типа
        rows = await conn.fetch(
            """
            SELECT id,
                   type,
                   login,
                   password,
                   proxy,
                   supplier_id,
                   buy_price,
                   receipt_state,
                   lifetime_minutes
            FROM resources
            WHERE type = $1
              AND manager_tg_id IS NULL
              AND status = 'free'
            ORDER BY id
            LIMIT $2
            """,
            r_type,
            count,
        )

        if not rows:
            await message.answer(
                f"Свободных ресурсов типа {r_type} сейчас нет. "
                f"Попроси администратора загрузить новые.",
                reply_markup=manager_menu_kb(),
            )
            await state.clear()
            return

        resource_ids = [row["id"] for row in rows]

        # ⚠️ ВАЖНО: статус больше НЕ меняем, только привязываем менеджера.
        await conn.execute(
            """
            UPDATE resources
            SET manager_tg_id = $1,
                issue_datetime = NOW()
            WHERE id = ANY($2::int[])
            """,
            message.from_user.id,
            resource_ids,
        )

        # Логируем в history
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
                    $1, $2, $3, $4, $5,
                    'issue',
                    $6, $7
                )
                """,
                row["id"],
                message.from_user.id,
                row["type"],
                row["supplier_id"],
                row["buy_price"],
                row["receipt_state"],
                row["lifetime_minutes"],
            )

    # Формируем сообщение менеджеру
    lines = ["Готово. Выдал ресурсы:\n"]
    for row in rows:
        login = row["login"]
        password = row["password"]
        proxy = row["proxy"]

        line = f"• <b>{r_type}</b> — <code>{login}</code> | <code>{password}</code>"
        if proxy:
            line += f" | proxy: <code>{proxy}</code>"
        lines.append(line)

    await message.answer("\n".join(lines), reply_markup=manager_menu_kb())
    await state.clear()
