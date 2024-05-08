import asyncio
from datetime import datetime, UTC
import logging
import traceback
from uuid import uuid4
import aiomqtt
import aioboto3
import orjson

import aiomysql
from config import settings


async def get_source_location(limit: int) -> dict:
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD.get_secret_value(),
        db=settings.MYSQL_DB,
        autocommit=False,
        loop=asyncio.get_event_loop(),
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                fetch_query = "SELECT * FROM source_location WHERE is_active = 0 ORDER BY id ASC LIMIT %s FOR UPDATE"
                await cur.execute(fetch_query, (limit,))
                locations = await cur.fetchall()
                location_ids = [str(location[0]) for location in locations]
                location_ids_str = ", ".join(map(str, location_ids))
                update_query = (
                    "UPDATE source_location SET is_active = 1 WHERE id IN (%s)"
                )
                await cur.execute(update_query, (location_ids_str,))
                await conn.commit()
                locations = [
                    {
                        "location_name": location[1],
                    }
                    for location in locations
                ]
                return locations
            except:
                await conn.rollback()
                raise


async def list_source_files(limit: int) -> list[dict]:
    source_locations = await get_source_location(limit)
    logging.info(f"Source locations: {source_locations}")
    return source_locations


async def publish_data(
    session: aioboto3.Session, client_id: str, source_file_name: str
):
    async with session.client("s3") as s3:
        try:
            response = await s3.get_object(
                Bucket=settings.S3_SOURCE_DATA_BUCKET, Key=f"{source_file_name}.json"
            )
            source_data = orjson.loads(await response["Body"].read())
            frequency = 1  # 1 second
            location_id = source_file_name.translate(str.maketrans("", "", ".json"))
            logging.info(f"Publishing data for location: {location_id}")
            async with aiomqtt.Client(
                identifier=client_id,
                hostname=settings.MQTT_BROKER_HOST,
                port=settings.MQTT_BROKER_PORT,
            ) as client:
                while True:
                    for data in source_data:
                        data["Date"] = datetime.now(UTC).isoformat()
                        await client.publish(
                            topic=f"{settings.MQTT_SOURCE_TOPIC}/{location_id}",
                            payload=orjson.dumps(data),
                        )
                        await asyncio.sleep(frequency)

        except Exception as error:
            traceback.print_exc()


async def main():
    logging.info("Getting source files")
    locations = await list_source_files(limit=50)
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
            client_id=str(uuid4()),
            source_file_name=location.get("location_name"),
        )
        tasks.append(task)
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    logging.info("Starting data generator")
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(main())
