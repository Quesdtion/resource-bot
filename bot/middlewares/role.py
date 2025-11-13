from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Any
from aiogram.types import Message, CallbackQuery


class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return await handler(event, data)

        # Пул БД берём из атрибута bot.db
        bot = data.get("bot")
        pool = getattr(bot, "db", None) if bot else None

        role = None
        if pool is not None:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT role FROM managers WHERE tg_id=$1",
                    from_user.id
                )
                if row:
                    role = row["role"]

        # Прокидываем роль в data, чтобы хендлеры могли её использовать
        data["role"] = role
        return await handler(event, data)
