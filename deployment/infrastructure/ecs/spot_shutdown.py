import json
import os
import sys
sys.path.append("../../")


import pulumi
import pulumi_aws as aws


from infrastructure.ecs.s3 import s3_lambda_function
from infrastructure.ecs.shared_ecs import role_stack, log_group
from infrastructure.environment import prefix, root_dir_relative
from infrastructure.ecs.api import api_on_demand_service, api_spot_service
from infrastructure.ecs.data_gererator import dg_on_demand_service
from infrastructure.ecs.mqtt import mqtt_on_demand_service
from infrastructure.ecs.kafka_mqtt_bridge import bridge_on_demand_service, bridge_spot_service
from infrastructure.ecs.data_processor import dp_on_demand_service, dp_spot_service

spot_shutdown_lambda_role_arn = role_stack.get_output("spot_shutdown_lambda_role_arn")


spot_shutdown_zip = aws.s3.BucketObject(
    f"{prefix}-spot-shutdown-zip",
    bucket=s3_lambda_function.id,
    source=pulumi.FileAsset(
        os.path.join(root_dir_relative, "spot-shutdown-handler/main.py")
    ),
    key="spot-shutdown-handler.zip",
)

spot_shutdown_lambda = aws.lambda_.Function(
    f"{prefix}-spot-shutdown-lambda",
    handler="main.handler",
    runtime=aws.lambda_.Runtime.PYTHON3D11,
    role=spot_shutdown_lambda_role_arn,
    s3_bucket=s3_lambda_function.bucket,
    s3_key=spot_shutdown_zip.key,
    s3_object_version=spot_shutdown_zip.version_id,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "LOG_GROUP_NAME": log_group.name,
            "PRIMARY_FALLBACK_MAPPING": json.dumps(
                {
                    api_spot_service.arn: api_on_demand_service.arn,
                    bridge_spot_service.arn: bridge_on_demand_service.arn,
                    dp_spot_service.arn: dp_on_demand_service.arn,
                }
            ),
        },
    ),
)
