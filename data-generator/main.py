import asyncio
from datetime import datetime, UTC
import logging
from uuid import uuid4
import aiomqtt
from boto3 import Session
import orjson

import aiomysql
from config import settings


async def get_source_location(limit: int) -> dict:
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DB,
        autocommit=True,
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            update_query = (
                "UPDATE source_location SET is_active = 1 WHERE is_active = 0 LIMIT %s"
            )
            await cur.execute(update_query, (limit,))

            fetch_query = "SELECT * FROM source_location WHERE is_active = 1 LIMIT %s ORDER BY id ASC"
            await cur.execute(fetch_query, (limit,))
            locations = await cur.fetchall()
            await conn.commit()
            return locations


async def list_source_files(limit: int) -> list[dict]:
    source_locations = await get_source_location(limit)
    return source_locations


async def publish_data(session: Session, client_id: str, source_file_name: str):
    s3 = session.client("s3")
    try:
        response = s3.get_object(
            Bucket=settings.S3_SOURCE_DATA_BUCKET, Key=source_file_name
        )
        source_data = orjson.loads(response["Body"].read())
        frequency = 1  # 1 second
        location_id = source_file_name.translate(str.maketrans("", "", ".csv"))
        logging.info(f"Publishing data for location: {location_id}")
        async with aiomqtt.Client(
            identifier=client_id,
            hostname=settings.MQTT_BROKER_HOST,
            port=settings.MQTT_BROKER_HOST,
        ) as client:
            for data in source_data:
                data["Date"] = datetime.now(UTC).isoformat()
                await client.publish(
                    topic=f"{settings.MQTT_SOURCE_TOPIC}/{location_id}",
                    payload=orjson.dumps(data),
                )
                await asyncio.sleep(frequency)

    except Exception as error:
        logging.error(f"Error: {error}")


async def main():
    locations = await list_source_files(limit=50)
    if not locations:
        return

    session = Session()
    tasks = []
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
    asyncio.run(main())
