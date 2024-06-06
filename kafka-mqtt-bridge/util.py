import logging
import aiohttp
import os

import botocore.exceptions

from aiobotocore.session import get_session
from config import settings

async def get_container_task_id():
    endpoint = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
    if endpoint is None:
        logging.error("ECS_CONTAINER_METADATA_URI_V4 environment variable not found")
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint) as response:
            if response.status == 200:
                meta_data = await response.json()
                task_arn = meta_data.get("TaskARN", "")
                task_id = task_arn.split("/")[-1]
                return task_id
            else:
                logging.error("Failed to get metadata: %s", response.content)
                return


async def sqs_shutdown_event_listener(handler: callable):
    running_task_id = await get_container_task_id()
    logging.debug(f"Task ID: {running_task_id}")

    session = get_session()
    async with session.create_client("sqs") as client:
        queue_url = settings.SHUTDOWN_QUEUE_URL

        while True:
            try:
                response = await client.receive_message(
                    QueueUrl=queue_url,
                    WaitTimeSeconds=20,
                )

                if "Messages" in response:
                    logging.debug("Received message", response["Messages"][0])
                    message = response["Messages"][0]
                    event_task_id = get_task_id_from_arn(message["detail"]["taskArn"])

                    if running_task_id == event_task_id:
                        logging.info("Received shutdown event")
                        await handler()

                    for msg in response["Messages"]:
                        await client.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=msg["ReceiptHandle"],
                        )
                        break
            except Exception as e:
                logging.exception("Error receiving message")


def get_task_id_from_arn(task_arn: str):
    return task_arn.split("/")[-1]
