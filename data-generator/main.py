import asyncio
from datetime import datetime, UTC
import logging
import traceback
from uuid import uuid4
import aiomqtt
import aioboto3
import orjson

from config import settings


async def publish_data(
    session: aioboto3.Session,
    source_file_name: str,
):
    async with session.client("s3") as s3:
        try:
            response = await s3.get_object(
                Bucket=settings.S3_SOURCE_DATA_BUCKET, Key=f"{source_file_name}.json"
            )
            source_data = orjson.loads(await response["Body"].read())
            frequency = 1  # 1 second
            location_id = source_file_name
            logging.info(f"Publishing data for location: {location_id}")
            async with aiomqtt.Client(
                identifier=str(uuid4()),
                hostname=settings.MQTT_BROKER_HOST,
                port=settings.MQTT_BROKER_PORT,
            ) as client:
                while True:
                    for data in source_data:
                        data["Date"] = (
                            datetime.now(UTC).replace(microsecond=0).isoformat()
                        )
                        data["location"] = location_id
                        await client.publish(
                            topic=f"{settings.MQTT_SOURCE_TOPIC}/{location_id}",
                            payload=orjson.dumps(data),
                        )
                        await asyncio.sleep(frequency)

        except Exception as error:
            traceback.print_exc()


async def on_message(client: aiomqtt.Client, userdata, message):
    return message.payload.decode()


async def main():
    client_id = str(uuid4())
    source_files = []
    async with aiomqtt.Client(
        identifier=client_id,
        hostname=settings.MQTT_BROKER_HOST,
        port=settings.MQTT_BROKER_PORT,
    ) as client:
        await client.subscribe("$share/dg/source_files")
        logging.info("waiting for messages")
        async for message in client.messages:
            source_files = await on_message(client, None, message)
            break  # Only process the first message

    logging.info(f"Received source files: {source_files}")
    locations = orjson.loads(source_files)
    if not locations:
        logging.warning("No source files found")
        return
    logging.info("Starting Boto3 session")
    session = aioboto3.Session()
    tasks = []
    logging.info("Publishing data")
    for location in locations:
        task = publish_data(
            session=session,
            source_file_name=location,
        )
        tasks.append(task)
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    logging.info("Starting data generator")
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(main())
