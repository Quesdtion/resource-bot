import os
import asyncpg

_pool = None


async def get_pool():
    """
    Возвращает единый пул соединений с БД.
    Создаётся один раз, затем переиспользуется.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            min_size=1,
            max_size=5,  # Можно уменьшить/увеличить при необходимости
        )
    return _pool
