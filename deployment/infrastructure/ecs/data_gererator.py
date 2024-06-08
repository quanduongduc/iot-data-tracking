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
data_generator_task_role_arn = role_stack.get_output("data_generator_task_role_arn")
data_generator_sg_id = network_stack.get_output("data_generator_sg_id")

data_generator_image = awsx.ecr.Image(
    f"{prefix}-dg-image",
    dockerfile=f"{root_dir_relative}/data-generator/Dockerfile",
    context=f"{root_dir_relative}/data-generator",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

data_generator_log_stream = aws.cloudwatch.LogStream(
    f"{prefix}-dg-log-stream",
    log_group_name=log_group.name,
)

data_generator_task_definition = aws.ecs.TaskDefinition(
    f"{prefix}-dg-task",
    family=f"{prefix}-dg-task",
    cpu="1024",
    memory="2048",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=task_execution_role_arn,
    task_role_arn=data_generator_task_role_arn,
    container_definitions=pulumi.Output.all(
        data_generator_image.image_uri, log_group.name, secret.name
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-dg-container",
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
                            "awslogs-stream-prefix": "dg",
                        },
                    },
                }
            ]
        ),
    ),
)

dg_on_demand_service, _ = generate_fargate_services(
    need_spot=False,
    prefix=f"{prefix}-dg",
    cluster=cluster.arn,
    task_definition=data_generator_task_definition.arn,
    desired_count=2,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        security_groups=[data_generator_sg_id],
        subnets=[ecs_private_subnet1_id, ecs_private_subnet2_id],
        assign_public_ip=False
    )
)
