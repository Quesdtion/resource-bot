from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from db.database import get_pool  # тот же модуль, что и в других хендлерах
from bot.utils.queries import DBQueries

router = Router()


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---


async def _issue_resource_for_manager(
    manager_tg_id: int,
    resource_type: str,
) -> tuple[dict | None, str]:
    """
    Выдаёт один свободный ресурс указанного типа менеджеру.
    Возвращает (resource_dict | None, error_message | "").
    """

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Ищем свободный ресурс нужного типа
        resource = await conn.fetchrow(DBQueries.GET_FREE_RESOURCE, resource_type)
        if not resource:
            return None, "Свободных ресурсов этого типа сейчас нет."

        # Помечаем ресурс выданным
        await conn.execute(
            DBQueries.ISSUE_RESOURCE,
            manager_tg_id,
            resource["id"],
        )

        # Пишем запись в историю
        await conn.execute(
            DBQueries.INSERT_HISTORY,
            resource["id"],                 # resource_id
            manager_tg_id,                  # manager_tg_id
            resource["type"],               # type
            resource["supplier_id"],        # supplier_id
            resource["buy_price"],          # price
            "issue",                        # action
            resource["receipt_state"],      # receipt_state
            resource["lifetime_minutes"],   # lifetime_minutes
        )

    # Превращаем Record в обычный dict для удобства
    return dict(resource), ""


# --- ХЕНДЛЕРЫ ---


@router.callback_query(F.data.startswith("issue_resource:"))
async def issue_resource_callback(callback: CallbackQuery):
    """
    Хендлер на нажатие кнопки вида:
    callback_data = "issue_resource:mamba" или "issue_resource:taboor" и т.п.
    """

    parts = callback.data.split(":", 1)
    if len(parts) != 2 or not parts[1]:
        await callback.answer("Некорректный формат запроса ресурса", show_alert=True)
        return

    resource_type = parts[1]

    resource, error = await _issue_resource_for_manager(
        manager_tg_id=callback.from_user.id,
        resource_type=resource_type,
    )

    if error:
        await callback.answer(error, show_alert=True)
        return

    # Отправляем данные ресурса менеджеру
    text_lines = [
        f"Ресурс типа <b>{resource['type']}</b> выдан:",
    ]
    if resource.get("login"):
        text_lines.append(f"🔑 Логин: <code>{resource['login']}</code>")
    if resource.get("password"):
        text_lines.append(f"🔒 Пароль: <code>{resource['password']}</code>")
    if resource.get("proxy"):
        text_lines.append(f"🌐 Прокси: <code>{resource['proxy']}</code>")

    await callback.message.answer("\n".join(text_lines))
    await callback.answer()


@router.message(F.text.in_({"/issue", "Выдать ресурс"}))
async def issue_resource_command(message: Message):
    """
    Запасной хендлер на случай, если вы хотите тестировать выдачу командой.
    Формат: /issue mamba
    """

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи тип ресурса, например: <code>/issue mamba</code>")
        return

    resource_type = parts[1].strip()

    resource, error = await _issue_resource_for_manager(
        manager_tg_id=message.from_user.id,
        resource_type=resource_type,
    )

    if error:
        await message.answer(error)
        return

    text_lines = [
        f"Ресурс типа <b>{resource['type']}</b> выдан:",
    ]
    if resource.get("login"):
        text_lines.append(f"🔑 Логин: <code>{resource['login']}</code>")
    if resource.get("password"):
        text_lines.append(f"🔒 Пароль: <code>{resource['password']}</code>")
    if resource.get("proxy"):
        text_lines.append(f"🌐 Прокси: <code>{resource['proxy']}</code>")

    await message.answer("\n".join(text_lines))
