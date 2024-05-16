import logging
import uuid
import aioboto3
import orjson
from config import settings
from aiokafka import AIOKafkaConsumer
import asyncio
from redis_db import async_hset_cache, async_redis
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
        session = aioboto3.Session()
        async with Client(
            identifier=client_id,
            hostname=settings.MQTT_BROKER_HOST,
            port=settings.MQTT_BROKER_PORT,
        ) as client, session.resource("dynamodb") as dynamo_resource:
            weather_table = await dynamo_resource.Table(settings.DYNAMODB_TABLE_NAME)
            async for msg in consumer:
                weather_data = orjson.loads(msg.value)

                if not await message_validator(weather_data):
                    continue

                processed_message = weather_data_processor(weather_data)

                await asyncio.gather(
                    store_weather_data(processed_message, weather_table),
                    publish_weather_data(
                        mqtt_client=client,
                        weather_data=processed_message,
                    ),
                )
    except Exception as e:
        logging.error(f"Error while consuming message: {e}")
    finally:
        await consumer.stop()


async def message_validator(weather_data: dict) -> bool:
    async with async_redis() as redis:
        last_weather_data = await redis.hget(
            "latest_weather_data", weather_data["location"]
        )
        if last_weather_data is not None:
            last_weather_data = orjson.loads(last_weather_data)
            if last_weather_data:
                if last_weather_data["Date"] >= weather_data["Date"]:
                    return False
    return True


def weather_data_processor(weather_data: dict) -> dict:
    return weather_data


async def publish_weather_data(mqtt_client: Client, weather_data: dict):
    await mqtt_client.publish(
        topic=f"{settings.MQTT_PROCESSED_TOPIC}/{weather_data['location']}",
        payload=orjson.dumps(weather_data),
    )


async def store_weather_data(weather_data: dict, weather_table):
    async with async_redis() as redis:
        data_dict = {k: str(v) for k, v in weather_data.items()}
        try:
            await async_hset_cache(
                redis=redis,
                name="latest_weather_data",
                key=weather_data["location"],
                data=weather_data,
            )
            await weather_table.put_item(Item=data_dict)
        except Exception as e:
            logging.error(f"Error occurred: {e}, data_dict: {data_dict}")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume())
