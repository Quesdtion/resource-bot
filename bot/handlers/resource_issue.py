# bot/handlers/resource_issue.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb
from bot.utils.admin_stats import send_free_resources_stats

router = Router()

# Типы ресурсов (как в загрузке)
RESOURCE_TYPES = ["mamba", "tabor", "beboo", "rambler"]

BACK_BUTTON = "⬅️ Назад"


def type_choice_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора типа ресурса при выдаче.
    """
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []

    for idx, t in enumerate(RESOURCE_TYPES, start=1):
        row.append(KeyboardButton(text=t))
        if idx % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([KeyboardButton(text=BACK_BUTTON)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def count_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора количества ресурсов 1–10.
    """
    rows = [
        [
            KeyboardButton(text="1"),
            KeyboardButton(text="2"),
            KeyboardButton(text="3"),
            KeyboardButton(text="4"),
            KeyboardButton(text="5"),
        ],
        [
            KeyboardButton(text="6"),
            KeyboardButton(text="7"),
            KeyboardButton(text="8"),
            KeyboardButton(text="9"),
            KeyboardButton(text="10"),
        ],
        [KeyboardButton(text=BACK_BUTTON)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


class IssueStates(StatesGroup):
    waiting_type = State()
    waiting_count = State()


# ==========================
# Старт выдачи ресурсов
# ==========================


@router.message(F.text == "📦 Получить ресурсы")
async def start_issue(message: Message, state: FSMContext):
    """
    Менеджер нажал кнопку 'Получить ресурсы'.
    """
    await state.set_state(IssueStates.waiting_type)
    await message.answer(
        "Выбери тип ресурса, который тебе нужен:",
        reply_markup=type_choice_kb(),
    )


# Назад / отмена
@router.message(IssueStates.waiting_type, F.text == BACK_BUTTON)
@router.message(IssueStates.waiting_count, F.text == BACK_BUTTON)
async def cancel_issue(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=manager_menu_kb())


# ==========================
# Выбор типа ресурса
# ==========================


@router.message(IssueStates.waiting_type)
async def choose_type(message: Message, state: FSMContext):
    r_type = (message.text or "").strip().lower()

    if r_type not in RESOURCE_TYPES:
        await message.answer(
            "Пожалуйста, выбери тип кнопкой ниже:",
            reply_markup=type_choice_kb(),
        )
        return

    await state.update_data(type=r_type)
    await state.set_state(IssueStates.waiting_count)

    await message.answer(
        "Сколько ресурсов тебе нужно (от 1 до 10)?",
        reply_markup=count_kb(),
    )


# ==========================
# Выбор количества и выдача
# ==========================


@router.message(IssueStates.waiting_count)
async def choose_count(message: Message, state: FSMContext, role: str | None = None):
    text = (message.text or "").strip()

    if text == BACK_BUTTON:
        # Назад к выбору типа
        await state.set_state(IssueStates.waiting_type)
        await message.answer(
            "Выбери тип ресурса, который тебе нужен:",
            reply_markup=type_choice_kb(),
        )
        return

    if not text.isdigit():
        await message.answer(
            "Введи число от 1 до 10 или нажми кнопку.",
            reply_markup=count_kb(),
        )
        return

    count = int(text)
    if not (1 <= count <= 10):
        await message.answer("Нужно число от 1 до 10.", reply_markup=count_kb())
        return

    data = await state.get_data()
    r_type = data.get("type")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Свободный ресурс = status='free' И manager_tg_id IS NULL
        rows = await conn.fetch(
            """
            SELECT id, login, password, proxy
            FROM resources
            WHERE status = 'free'
              AND manager_tg_id IS NULL
              AND type = $1
            ORDER BY id
            LIMIT $2
            """,
            r_type,
            count,
        )

        if not rows:
            await state.clear()
            await message.answer(
                f"Свободных ресурсов типа <b>{r_type}</b> сейчас нет. "
                f"Попроси администратора загрузить новые.",
                reply_markup=manager_menu_kb(),
            )
            return

        ids = [r["id"] for r in rows]

        # ❗ Статус НЕ трогаем, чтобы не ломать CHECK-constraint.
        # Занятость определяем только по manager_tg_id.
        await conn.execute(
            """
            UPDATE resources
            SET manager_tg_id = $1
            WHERE id = ANY($2::int[])
            """,
            message.from_user.id,
            ids,
        )

    # Формируем красивый вывод
    issued_count = len(rows)
    lines = [f"📦 Выдано ресурсов: {issued_count} (тип: {r_type})", ""]
    for idx, row in enumerate(rows, start=1):
        login = row["login"]
        password = row["password"]
        line = f"{idx}) {login} | {password}"

        proxy = row.get("proxy")
        if proxy:
            line += f" | proxy: {proxy}"

        lines.append(line)

    await message.answer("\n".join(lines), reply_markup=manager_menu_kb())
    await state.clear()

    # После выдачи показываем статистику свободных ресурсов только админу
    if role == "admin":
        await send_free_resources_stats(message)
