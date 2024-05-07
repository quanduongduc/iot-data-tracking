import decimal
from typing import AsyncIterator
import orjson
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError
import redis.asyncio as redis
from async_generator import asynccontextmanager

from .config import settings


redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)
redis_session: AsyncRedis = AsyncRedis(connection_pool=redis_pool)


@asynccontextmanager
async def async_redis() -> AsyncIterator[AsyncRedis]:
    try:
        yield redis_session
    except RedisError as e:
        raise e
    finally:
        await redis_session.close()


def value_serializer(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


async def async_set_cache(redis: AsyncRedis, key, data, expire=None):
    if isinstance(data, dict):
        data = orjson.dumps(data, default=value_serializer)

    await redis.set(name=key, value=data, ex=expire)


async def async_hset_cache(redis: AsyncRedis, name: str, key: str, data, expire=None):
    if isinstance(data, dict):
        data = orjson.dumps(data, default=value_serializer)

    await redis.hset(name=name, key=key, value=data)
    if expire:
        await redis.expire(name, expire)
