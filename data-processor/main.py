import logging
import uuid
import aioboto3
import orjson
from config import settings
from aiokafka import AIOKafkaConsumer
import asyncio
from redis_db import async_hset_cache, async_redis
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
            async for msg in consumer:
                dict_data = orjson.loads(msg.value)
                weather_data = WeatherData(**dict_data)

                if not await message_validator(weather_data):
                    continue

                processed_message = weather_data_processor(weather_data)

                await asyncio.gather(
                    store_weather_data(
                        processed_message
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
    session = aioboto3.Session()

    async with async_redis() as redis:
        async with session.resource('dynamodb') as dynamo_resource:
            data_dict = weather_data.model_dump()
            data_dict["Date"] = data_dict["Date"].isoformat()
            logging.info(f"Storing weather data: {weather_data['location']}")

            try:
                await async_hset_cache(
                    redis=redis,
                    name="latest_weather_data",
                    key=weather_data.location,
                    data=weather_data.model_dump(),
                )

                await dynamo_resource.Table(settings.DYNAMODB_TABLE_NAME).put_item(
                    Item=data_dict
                )
            except Exception as e:
                logging.error(f"Error occurred: {e}, data_dict: {data_dict}")
                raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume())
