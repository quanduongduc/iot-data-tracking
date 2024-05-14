from contextlib import asynccontextmanager
import aiomysql
from config import settings

pool = None


async def create_pool():
    global pool
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD.get_secret_value(),
        db=settings.MYSQL_DB,
    )


@asynccontextmanager
async def get_db_connection():
    global pool
    if pool is None:
        await create_pool()

    try:
        async with pool.acquire() as conn:
            yield conn
    finally:
        if pool is not None:
            pool.close()
            await pool.wait_closed()
            pool = None
