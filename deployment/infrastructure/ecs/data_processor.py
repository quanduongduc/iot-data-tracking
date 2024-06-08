import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

from infrastructure.environment import prefix, region, root_dir_relative, stack_name
from infrastructure.ecs.secrets_manager import secret
from infrastructure.ecs.shared_ecs import (
    cluster,
    generate_fargate_services,
    repo,
    log_group,
    network_stack,
    role_stack,
)


ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
vpc_id = network_stack.get_output("vpc_id")
task_execution_role_arn = role_stack.get_output("task_execution_role_arn")
data_processor_task_role_arn = role_stack.get_output("data_processor_task_role_arn")
ec2_data_processor_role_name = role_stack.get_output("ec2_data_processor_role_name")
data_processor_sg_id = network_stack.get_output("data_processor_sg_id")

data_processor_image = awsx.ecr.Image(
    f"{prefix}-dp-image",
    dockerfile=f"{root_dir_relative}/data-processor/Dockerfile",
    context=f"{root_dir_relative}/data-processor",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

data_processor_log_stream = aws.cloudwatch.LogStream(
    f"{prefix}-dp-log-stream",
    log_group_name=log_group.name,
)

data_processor_task_definition = aws.ecs.TaskDefinition(
    f"{prefix}-dp-task",
    family=f"{prefix}-dp-task",
    cpu="1024",
    memory="2048",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    task_role_arn=data_processor_task_role_arn,
    execution_role_arn=task_execution_role_arn,
    container_definitions=pulumi.Output.all(
        data_processor_image.image_uri, log_group.name, secret.name
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-dp-container",
                    "image": args[0],
                    "environment": [
                        {"name": "ENVIRONMENT", "value": f"{stack_name.upper()}"},
                        {"name": "AWS_SECRET_ID", "value": f"{args[2]}"},
                        {"name": "AWS_DEFAULT_REGION", "value": f"{region}"},
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": args[1],
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "dp",
                        },
                    },
                }
            ]
        ),
    ),
)

dp_on_demand_service, dp_spot_service = generate_fargate_services(
    prefix=f"{prefix}-dp",
    cluster=cluster.arn,
    task_definition=data_processor_task_definition.arn,
    desired_count=2,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        assign_public_ip=False,
        security_groups=[data_processor_sg_id],
        subnets=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    ),
)
