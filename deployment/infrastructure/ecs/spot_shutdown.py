import json
import os
import sys
import zipfile
sys.path.append("../../")


import pulumi
import pulumi_aws as aws


from infrastructure.ecs.s3 import s3_lambda_function
from infrastructure.ecs.shared_ecs import role_stack, log_group
from infrastructure.environment import prefix, root_dir_relative
from infrastructure.ecs.api import api_on_demand_service, api_spot_service
from infrastructure.ecs.data_gererator import dg_on_demand_service
from infrastructure.ecs.kafka_mqtt_bridge import bridge_on_demand_service, bridge_spot_service
from infrastructure.ecs.data_processor import dp_on_demand_service, dp_spot_service
from infrastructure.ecs.shared_ecs import cluster

spot_shutdown_lambda_role_arn = role_stack.get_output("spot_shutdown_lambda_role_arn")

zip_function_folder = os.path.join(root_dir_relative, "zip-function")
os.makedirs(zip_function_folder, exist_ok=True)

zip_shut_down_file_path = os.path.join(zip_function_folder, "spot-shutdown-handler.zip")
spot_function_dir = os.path.join(root_dir_relative, "spot-shutdown-handler")

with zipfile.ZipFile(zip_shut_down_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk(spot_function_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, spot_function_dir)
            zipf.write(
                filename=file_path,
                arcname=arcname,
            )


spot_shutdown_zip = aws.s3.BucketObject(
    f"{prefix}-spot-shutdown-zip",
    bucket=s3_lambda_function.id,
    source=pulumi.FileAsset(zip_shut_down_file_path),
    key="spot-shutdown-handler.zip",
)

env_vars = pulumi.Output.all(
    log_group.name,
    api_spot_service.name,
    api_on_demand_service.name,
    bridge_spot_service.name,
    bridge_on_demand_service.name,
    dp_spot_service.name,
    dp_on_demand_service.name,
    None,
    dg_on_demand_service.name,
).apply(
    lambda args: {
        "LOG_GROUP_NAME": args[0],
        "PRIMARY_FALLBACK_MAPPING": json.dumps(
            {
                args[1]: args[2],
                args[3]: args[4],
                args[5]: args[6],
                args[7]: args[8],
            }
        ),
    }
)

spot_shutdown_lambda = aws.lambda_.Function(
    f"{prefix}-spot-shutdown-lambda",
    handler="main.handler",
    runtime=aws.lambda_.Runtime.PYTHON3D11,
    role=spot_shutdown_lambda_role_arn,
    s3_bucket=s3_lambda_function.bucket,
    s3_key=spot_shutdown_zip.key,
    s3_object_version=spot_shutdown_zip.version_id,
    environment=aws.lambda_.FunctionEnvironmentArgs(variables=env_vars),
)

placement_failure_rule = aws.cloudwatch.EventRule(
    f"{prefix}-spot-pf-rule",
    event_pattern=pulumi.Output.all(cluster.arn).apply(
        lambda arn: json.dumps(
            {
                "source": ["aws.ecs"],
                "detail-type": ["ECS Deployment State Change"],
                "detail": {
                    "eventName": ["SERVICE_TASK_PLACEMENT_FAILURE"],
                    "clusterArn": arn,
                    "reason": ["RESOURCE:FARGATE"],
                },
            }
        )
    ),
)

placement_failure_event_target = aws.cloudwatch.EventTarget(
    f"{prefix}-spot-pf-target",
    rule=placement_failure_rule.name,
    arn=spot_shutdown_lambda.arn,
)

ready_state_event_rule = aws.cloudwatch.EventRule(
    f"{prefix}-spot-ready-state-rule",
    event_pattern=pulumi.Output.all(cluster.arn).apply(
        lambda arn: json.dumps(
            {
                "source": ["aws.ecs"],
                "detail-type": ["ECS Service Action"],
                "detail": {
                    "eventName": ["SERVICE_STEADY_STATE"],
                    "clusterArn": arn,
                },
            }
        )
    ),
)


placement_failure_lambda_permission = aws.lambda_.Permission(
    f"{prefix}-rf-lambda-permission",
    action="lambda:InvokeFunction",
    function=spot_shutdown_lambda.name,
    principal="events.amazonaws.com",
    source_arn=placement_failure_rule.arn
)

ready_state_lambda_permission = aws.lambda_.Permission(
    f"{prefix}-ready_state-lambda-permission",
    action="lambda:InvokeFunction",
    function=spot_shutdown_lambda.name,
    principal="events.amazonaws.com",
    source_arn=ready_state_event_rule.arn,
)