from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.database import get_pool
from bot.handlers.manager_menu import manager_menu_kb, BACK_BUTTON_TEXT

router = Router()

# -------------------------------------------------
# Константы
# -------------------------------------------------

RESOURCE_TYPES = ["mamba", "tabor", "beboo", "rambler"]


def resource_type_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора типа ресурса.
    """
    row = [KeyboardButton(text=t) for t in RESOURCE_TYPES]
    return ReplyKeyboardMarkup(
        keyboard=[
            row,
            [KeyboardButton(text=BACK_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
    )


def resource_count_kb() -> ReplyKeyboardMarkup:
    """
    Клавиатура выбора количества (1–10).
    """
    keyboard = [
        [KeyboardButton(text=str(i)) for i in range(1, 6)],
        [KeyboardButton(text=str(i)) for i in range(6, 11)],
        [KeyboardButton(text=BACK_BUTTON_TEXT)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# -------------------------------------------------
# Состояния
# -------------------------------------------------

class IssueStates(StatesGroup):
    waiting_type = State()
    waiting_count = State()


# -------------------------------------------------
# Старт выдачи ресурсов
# -------------------------------------------------

@router.message(F.text == "📦 Получить ресурсы")
@router.message(Command("get"))
async def start_issue(message: Message, state: FSMContext):
    """
    Старт сценария выдачи ресурсов менеджеру.
    """
    await state.set_state(IssueStates.waiting_type)
    await message.answer(
        "Выбери тип ресурса, который тебе нужен:",
        reply_markup=resource_type_kb(),
    )


# -------------------------------------------------
# Обработка кнопки Назад
# -------------------------------------------------

@router.message(F.text == BACK_BUTTON_TEXT)
async def back_to_menu(message: Message, state: FSMContext):
    """
    Глобальная обработка кнопки 'Назад' – возвращаем в главное меню.
    """
    await state.clear()
    await message.answer("Главное меню:", reply_markup=manager_menu_kb())


# -------------------------------------------------
# Выбор типа ресурса
# -------------------------------------------------

@router.message(IssueStates.waiting_type)
async def choose_type(message: Message, state: FSMContext):
    text = (message.text or "").strip().lower()

    if text == BACK_BUTTON_TEXT:
        return await back_to_menu(message, state)

    if text not in RESOURCE_TYPES:
        await message.answer(
            "Выбери тип ресурса с помощью кнопки ниже:",
            reply_markup=resource_type_kb(),
        )
        return

    await state.update_data(r_type=text)
    await state.set_state(IssueStates.waiting_count)
    await message.answer(
        "Сколько ресурсов тебе нужно (от 1 до 10)?",
        reply_markup=resource_count_kb(),
    )


# -------------------------------------------------
# Выбор количества и выдача
# -------------------------------------------------

@router.message(IssueStates.waiting_count)
async def choose_count(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == BACK_BUTTON_TEXT:
        return await back_to_menu(message, state)

    # Парсим число
    try:
        count = int(text)
    except ValueError:
        await message.answer(
            "Введи число от 1 до 10 или выбери на клавиатуре:",
            reply_markup=resource_count_kb(),
        )
        return

    if not (1 <= count <= 10):
        await message.answer(
            "Можно запросить от 1 до 10 ресурсов.",
            reply_markup=resource_count_kb(),
        )
        return

    data = await state.get_data()
    r_type = data.get("r_type")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Берём свободные ресурсы:
        # Свободный = manager_tg_id IS NULL
        rows = await conn.fetch(
            """
            SELECT id, login, password, proxy
            FROM resources
            WHERE type = $1
              AND manager_tg_id IS NULL
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

        ids = [row["id"] for row in rows]

        # Отмечаем ресурсы за менеджером + пишем в историю
        async with conn.transaction():
            # Обновляем ресурсы: привязываем к менеджеру
            await conn.execute(
                """
                UPDATE resources
                SET manager_tg_id = $1,
                    issue_datetime = NOW(),
                    receipt_state = 'new'
                WHERE id = ANY($2::int[])
                """,
                message.from_user.id,
                ids,
            )

            # Лог в history
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
                SELECT
                    NOW(),
                    r.id,
                    $1,
                    r.type,
                    r.supplier_id,
                    r.buy_price,
                    'issue',
                    r.receipt_state,
                    r.lifetime_minutes
                FROM resources r
                WHERE r.id = ANY($2::int[])
                """,
                message.from_user.id,
                ids,
            )

    # Формируем аккуратный вывод
    header = f"📦 Выдано ресурсов: {len(rows)} (тип: {r_type})\n\n"
    lines = []

    for idx, r in enumerate(rows, start=1):
        login = r["login"]
        password = r["password"]
        lines.append(f"{idx}) {login} | {password}")

    text = header + "\n".join(lines)

    await message.answer(text, reply_markup=manager_menu_kb())
    await state.clear()
