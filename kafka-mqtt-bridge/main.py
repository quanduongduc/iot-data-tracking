import asyncio
import logging
import traceback
import uuid

import aiomqtt
import orjson
from config import settings
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError


async def publish_to_kafka(producer: AIOKafkaProducer, data: dict):
    try:
        await producer.send(settings.KAFKA_WEATHER_DATA_TOPIC, orjson.dumps(data))
    except KafkaError as e:
        logging.error(f"Error while publishing to Kafka: {e}")


async def bridge():
    try:
        client_id = uuid.uuid4().hex
        async with aiomqtt.Client(
            identifier=client_id,
            hostname=settings.MQTT_BROKER_HOST,
            port=settings.MQTT_BROKER_PORT,
        ) as client, AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
        ) as producer:
            await producer.start()
            await client.subscribe(f"{settings.MQTT_SOURCE_TOPIC}/#")
            async for message in client.messages:
                try:
                    data = orjson.loads(message.payload)
                    await publish_to_kafka(producer, data)
                except Exception as error:
                    logging.error(f"Error while processing message: {error}")

    except Exception as error:
        traceback.print_exc()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting Kafka MQTT Bridge")
    asyncio.run(bridge())
