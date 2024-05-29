import json
import os
import boto3
import logging


def handler(event, context):
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Creating ECS client")
    ecs_client = boto3.client("ecs")

    primary_service_arn = get_service_arn(event)
    try:
        primary_fallback_mapping: dict = json.loads(os.environ.get("PRIMARY_FALLBACK_MAPPING"))
        if primary_fallback_mapping is None or not isinstance(primary_fallback_mapping, dict):
            logging.error("PRIMARY_FALLBACK_MAPPING environment variable not found or not a dictionary")
            return
        
        if primary_service_arn not in primary_fallback_mapping:
            logging.error(f"Primary service ARN {primary_service_arn} not found in PRIMARY_FALLBACK_MAPPING")
            return
        
    except json.JSONDecodeError:
        logging.error("Error parsing PRIMARY_FALLBACK_MAPPING environment variable")
        return
    
    fallback_service_arn = primary_fallback_mapping.get(primary_service_arn)

    logging.info(f"Primary Service ARN: {primary_service_arn}")
    logging.info(f"Fallback Service ARN: {fallback_service_arn}")

    event_name = get_event_name(event)
    cluster_arn = get_cluster_arn(event)
    
    if event_name == "SERVICE_TASK_PLACEMENT_FAILURE":
        logging.info("Service task failed to be placed. Initiating fallback.")

        logging.info(f"Describing {primary_service_arn} in cluster {cluster_arn}")
        result = ecs_client.describe_services(
            cluster=cluster_arn, services=[primary_service_arn]
        )
        primary_service_desired_count = result["services"][0]["desiredCount"]

        logging.info(
            f"Setting desired count of {fallback_service_arn} to {primary_service_desired_count}"
        )

        ecs_client.update_service(
            cluster=cluster_arn,
            service=fallback_service_arn,
            desiredCount=primary_service_desired_count,
        )

    elif event_name == "SERVICE_STEADY_STATE":
        logging.info("The primary service reached steady state.")
        logging.info(f"Setting desired count of {fallback_service_arn} to 0")

        ecs_client.update_service(
            cluster=cluster_arn, service=fallback_service_arn, desiredCount=0
        )

    else:
        logging.warn(f"Received an unsupported event {event_name}")


def get_event_name(event):
    return (
        event["detail"]["eventName"]
        if event and event["detail"] and event["detail"]["eventName"]
        else None
    )


def get_fallback_service_arn(primary_service_arn: str):
    return primary_service_arn.replace("primary", "fallback")

def get_service_arn(event):
    return (
        event["resources"][0]
        if event and "resources" in event and len(event["resources"]) > 0
        else None
    )

def get_cluster_arn(event):
    return (
        event["detail"]["clusterArn"]
        if event and event["detail"] and event["detail"]["clusterArn"]
        else None
    )
