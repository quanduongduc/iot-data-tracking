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
            location_ids = await get_location_ids()
            async for msg in consumer:
                dict_data = orjson.loads(msg.value)
                weather_data = WeatherData(**dict_data)

                if not await message_validator(weather_data):
                    continue

                processed_message = weather_data_processor(weather_data)

                await asyncio.gather(
                    store_weather_data(
                        processed_message,
                        location_ids,
                    ),
                    publish_weather_data(
                        mqtt_client=client,
                        weather_data=processed_message,
                    ),
                )
    except Exception as e:
        logging.error(f"Error while consuming message: {e}")
    finally:
        await consumer.stop()


async def get_location_ids():
    async with get_db_connection() as db_connection:
        async with db_connection.cursor() as cur:
            await cur.execute("SELECT id, name FROM source_location")
            location_ids = await cur.fetchall()
    return {location[1]: location[0] for location in location_ids}


async def message_validator(weather_data: WeatherData) -> bool:
    async with async_redis() as redis:
        last_weather_data = await redis.hget(
            "latest_weather_data", weather_data.location
        )
        if last_weather_data is not None:
            last_weather_data = orjson.loads(last_weather_data)
            if last_weather_data:
                logging.info(f"Last weather data: {last_weather_data}")
                logging.info(f"Current weather data: {weather_data}")
                last_weather_data = WeatherData(**last_weather_data)
                if last_weather_data.Date >= weather_data.Date:
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


async def publish_weather_data(mqtt_client: Client, weather_data: PublishWeatherData):
    await mqtt_client.publish(
        topic=f"{settings.MQTT_PROCESSED_TOPIC}/{weather_data.location}",
        payload=orjson.dumps(weather_data.model_dump()),
    )


async def store_weather_data(weather_data: StoreWeatherData, location_ids: dict):
    logging.info(f"Storing weather data: {weather_data}")
    logging.info(f"Location ids: {location_ids}")
    async with async_redis() as redis, get_db_connection() as db_connection:
        async with db_connection.cursor() as cur:
            location_id = location_ids.get(weather_data.location)
            data_dict = weather_data.model_dump(exclude=["location"])
            if not location_id:
                return
            logging.info(f"Storing weather data: {location_id}")

            try:
                await async_hset_cache(
                    redis=redis,
                    name="latest_weather_data",
                    key=weather_data.location,
                    data=weather_data.model_dump(),
                )

                await cur.execute(
                    """
                        INSERT INTO weather_data (
                            location_id, temperature, humidity, wind_speed, wind_direction, 
                            rain_fall, date, latitude, longitude, cld, pet, tmn, tmx, wet
                        )  
                        VALUES (
                            %(location_id)s, %(tmp)s, %(vap)s, %(frs)s, %(dtr)s, %(pre)s, %(Date)s, %(Latitude)s, 
                            %(Longitude)s, %(cld)s, %(pet)s, %(tmn)s, %(tmx)s, %(wet)s
                        )
                        """,
                    {
                        "location_id": location_id,
                        "tmp": data_dict["tmp"],
                        "vap": data_dict["vap"],
                        "frs": data_dict["frs"],
                        "dtr": data_dict["dtr"],
                        "pre": data_dict["pre"],
                        "Date": data_dict["Date"].isoformat(),
                        "Latitude": data_dict["Latitude"],
                        "Longitude": data_dict["Longitude"],
                        "cld": data_dict["cld"],
                        "pet": data_dict["pet"],
                        "tmn": data_dict["tmn"],
                        "tmx": data_dict["tmx"],
                        "wet": data_dict["wet"],
                    },
                ),
                await db_connection.commit()
            except Exception as e:
                logging.error(f"Error occurred: {e}, data_dict: {data_dict}")
                raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume())
