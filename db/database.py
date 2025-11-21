# db/database.py
import os
import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """
    Возвращает общий пул соединений с БД.
    При первом вызове создаёт пул, дальше переиспользует.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )
    return _pool
