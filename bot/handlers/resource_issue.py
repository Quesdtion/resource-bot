# bot/handlers/resource_issue.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.utils.queries import DBQueries
from bot.handlers.manager_menu import manager_menu_kb
from bot.utils.admin_stats import send_free_resources_stats

router = Router()

BACK_BUTTON = "⬅️ Назад"

# Те же типы, что и в загрузке
RESOURCE_TYPES = ["mamba", "tabor", "beboo", "rambler"]


def resource_types_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t) for t in RESOURCE_TYPES],
            [KeyboardButton(text=BACK_BUTTON)],
        ],
        resize_keyboard=True,
    )


def count_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура с выбором количества 1–10 и кнопкой Назад.
    """
    rows = []
    numbers = [str(i) for i in range(1, 11)]
    # по 5 в ряд
    for i in range(0, 10, 5):
        row = [KeyboardButton(text=numbers[j]) for j in range(i, i + 5)]
        rows.append(row)

    rows.append([KeyboardButton(text=BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# ------------------------------
# FSM
# ------------------------------


class IssueStates(StatesGroup):
    waiting_type = State()
    waiting_count = State()


# ------------------------------
# Старт выдачи ресурсов
# ------------------------------


@router.message(F.text == "📦 Получить ресурсы")
async def issue_start(message: Message, state: FSMContext):
    await state.set_state(IssueStates.waiting_type)
    await message.answer(
        "Выбери тип ресурса, который тебе нужен:",
        reply_markup=resource_types_kb(),
    )


@router.message(F.text == BACK_BUTTON, IssueStates)
async def issue_back_any(message: Message, state: FSMContext):
    """
    Назад из любого шага выдачи ресурсов — в главное меню.
    """
    await state.clear()
    await message.answer("Главное меню", reply_markup=manager_menu_kb())


# ------------------------------
# Выбор типа
# ------------------------------


@router.message(IssueStates.waiting_type)
async def choose_issue_type(message: Message, state: FSMContext):
    r_type = (message.text or "").strip().lower()

    if r_type not in RESOURCE_TYPES:
        await message.answer("Пожалуйста, выбери тип ресурса кнопкой.", reply_markup=resource_types_kb())
        return

    await state.update_data(type=r_type)
    await state.set_state(IssueStates.waiting_count)

    await message.answer(
        "Сколько ресурсов тебе нужно (от 1 до 10)?",
        reply_markup=count_kb(),
    )


# ------------------------------
# Выбор количества и выдача
# ------------------------------


@router.message(IssueStates.waiting_count)
async def choose_count(
    message: Message,
    state: FSMContext,
    role: str | None = None,
):
    text = (message.text or "").strip()

    if text == BACK_BUTTON:
        # Назад к выбору типа
        await state.set_state(IssueStates.waiting_type)
        await message.answer(
            "Выбери тип ресурса, который тебе нужен:",
            reply_markup=resource_types_kb(),
        )
        return

    if not text.isdigit():
        await message.answer("Введи число от 1 до 10 или нажми кнопку.", reply_markup=count_kb())
        return

    count = int(text)
    if count < 1 or count > 10:
        await message.answer("Можно запросить от 1 до 10 ресурсов.", reply_markup=count_kb())
        return

    data = await state.get_data()
    r_type = data.get("type")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # 1) берём свободные ресурсы нужного типа
        rows = await conn.fetch(
            DBQueries.GET_FREE_RESOURCES,
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

        resource_ids = [r["id"] for r in rows]

        # 2) помечаем их как выданные
        await conn.execute(
            DBQueries.ISSUE_RESOURCES,
            resource_ids,
            message.from_user.id,
        )

        # 3) логируем в history
        for r in rows:
            await conn.execute(
                DBQueries.HISTORY_LOG,
                r["id"],
                message.from_user.id,
                "issue",
            )

    # Формируем выдачу в нужном формате
    lines = [f"📦 Выдано ресурсов: {len(rows)} (тип: {r_type})", ""]
    for idx, r in enumerate(rows, start=1):
        login = r["login"]
        password = r["password"]
        proxy = r.get("proxy")

        line = f"{idx}) {login} | {password}"
        if proxy:
            line += f" | proxy: {proxy}"
        lines.append(line)

    await message.answer("\n".join(lines), reply_markup=manager_menu_kb())
    await state.clear()

    # 🔹 После выдачи — показать статистику только админу
    if role == "admin":
        await send_free_resources_stats(message)
