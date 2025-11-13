import asyncpg
from bot.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from . import init_db

async def create_pool():
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        min_size=1,
        max_size=10,
    )
    async with pool.acquire() as conn:
        await init_db.ensure_schema(conn)
    return pool
