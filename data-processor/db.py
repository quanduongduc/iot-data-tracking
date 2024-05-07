import aiomysql
from async_generator import asynccontextmanager
from config import settings

@asynccontextmanager
async def get_db_connection():
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DB,
    )
    try:
        async with pool.acquire() as conn:
            yield conn
    finally:
        pool.close()
        await pool.wait_closed()
