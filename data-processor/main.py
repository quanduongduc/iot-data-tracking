from datetime import datetime
import logging
import uuid

import orjson
from config import settings
from aiokafka import AIOKafkaConsumer
import asyncio
from redis_db import async_hset_cache, async_redis
from db import get_db_connection
from models import WeatherData, StoreWeatherData, PublishWeatherData
from aiomqtt import Client
from aiokafka import TopicPartition


async def consume():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_WEATHER_DATA_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_WEATHER_DATA_GROUP_ID,
    )
    await consumer.start()
    try:
        client_id = uuid.uuid4().hex
        async with Client(
            identifier=client_id,
            hostname=settings.MQTT_BROKER_HOST,
            port=settings.MQTT_BROKER_PORT,
        ) as client:
            async for msg in consumer:
                dict_data = orjson.loads(msg.value)
                if not dict_data["pet"]:
                    logging.error(f"Invalid message: {dict_data}")
                weather_data = WeatherData(**dict_data)

                if not await message_validator(weather_data):
                    continue

                processed_message = weather_data_processor(weather_data)

                await asyncio.gather(
                    store_weather_data(processed_message),
                    publish_weather_data(mqtt_client=client, data=processed_message),
                )
    except Exception as e:
        logging.error(f"Error while consuming message: {e}")
    finally:
        await consumer.stop()


async def message_validator(weather_data: WeatherData) -> bool:
    async with async_redis() as redis:
        last_weather_data = await redis.hget(
            "lastest_weather_data", weather_data.location
        )
        if last_weather_data:
            last_weather_data = StoreWeatherData(**last_weather_data)
            if last_weather_data.Date > weather_data.Date:
                return False
    return True


def weather_data_processor(weather_data: WeatherData) -> StoreWeatherData:
    return StoreWeatherData(
        location=weather_data.location,
        Date=weather_data.Date,
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


async def publish_weather_data(client: Client, weather_data: PublishWeatherData):
    await client.publish(
        topic=f"{settings.MQTT_PROCESSED_TOPIC}/{weather_data.location}",
        payload=orjson.dumps(weather_data.model_dump()),
    )


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
