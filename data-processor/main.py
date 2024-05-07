from datetime import datetime
from config import settings
from aiokafka import AIOKafkaConsumer
import asyncio
from redis_db import async_hset_cache, async_redis
from db import get_db_connection
from models import WeatherData, StoreWeatherData, PublishWeatherData


async def consume():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_WEATHER_DATA_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_WEATHER_DATA_GROUP_ID,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            weather_data = WeatherData(**msg.value)

            if not await message_validator(weather_data):
                continue

            processed_message = weather_data_processor(weather_data)

            await asyncio.gather(
                store_weather_data(processed_message),
                publish_weather_data(processed_message),
            )
    finally:
        await consumer.stop()


async def message_validator(weather_data: WeatherData) -> bool:
    async with async_redis() as redis:
        last_weather_data = await redis.hget(
            "lastest_weather_data", weather_data.location
        )
        if last_weather_data:
            last_weather_data = StoreWeatherData(**last_weather_data)
            if last_weather_data.time > weather_data.time:
                return False
    return True


def weather_data_processor(weather_data: WeatherData) -> StoreWeatherData:
    return StoreWeatherData(
        location=weather_data.location,
        time=weather_data.time,
        Latitude=weather_data.Latitude,
        Longitude=weather_data.Longitude,
        cld=weather_data.cld,
        dtr=weather_data.dtr,
        frs=weather_data.frs,
        pet=weather_data.pet,
        pre=weather_data.pre,
        tmn=weather_data.tmn,
        tmp=weather_data.tmp,
        tmx=weather_data.tmx,
        vap=weather_data.vap,
        wet=weather_data.wet,
    )


async def publish_weather_data(weather_data: PublishWeatherData):
    pass


async def store_weather_data(weather_data: StoreWeatherData):
    async with async_redis() as redis, get_db_connection() as db_connection:
        async with db_connection.cursor() as cur:
            await async_hset_cache(
                redis=redis,
                name="lastest_weather_data",
                key=weather_data.location,
                data=weather_data.model_dump(),
            )
            await cur.execute(
                "INSERT INTO weather_data (location, time) VALUES (:location, :time)",
                weather_data.model_dump(),
            )


if __name__ == "__main__":
    asyncio.run(consume())
