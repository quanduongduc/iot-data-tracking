import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
from vpc import ecs_subnet1, ecs_subnet2, api_sg
from environment import prefix, stack_name
from role import task_execution_role

cluster = aws.ecs.Cluster(f"{prefix}-cluster")

repo = aws.ecr.Repository(
    f"{prefix}-repo",
    force_delete=True,
    opts=pulumi.ResourceOptions(additional_secret_outputs=["repository_url"]),
)

api_docker_file = f"../Dockerfile.{stack_name}"
api_image = awsx.ecr.Image(
    f"{prefix}-fastapi-image",
    dockerfile=api_docker_file,
    context="../..",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

api_task_definition = aws.ecs.TaskDefinition(
    f"{prefix}-api-task",
    family=f"{prefix}-api-task",
    cpu="256",
    memory="512",
    network_mode="awsvpc",
    requires_compatibilities=["EC2"],
    execution_role_arn=task_execution_role.arn,
    container_definitions=pulumi.Output.all(
        repo.repository_url, api_image.image_uri
    ).apply(
        lambda args: f"""[
            {{
                "name": "{prefix}-api-container",
                "image": "{args[0]}:{args[1]}",
                "portMappings": [
                    {{
                        "containerPort": 80,
                        "hostPort": 80
                    }}
                ]
            }}
        ]"""
    ),
)

api_service = aws.ecs.Service(
    f"{prefix}-api-service",
    cluster=cluster.arn,
    task_definition=api_task_definition.arn,
    launch_type="EC2",
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        subnets=[
            ecs_subnet1.id,
            ecs_subnet2.id,
        ],
        assign_public_ip=False,
        security_groups=[
            api_sg.id,
        ],
    ),
    desired_count=2,
)

pulumi.export("api_service_name", api_service.name)
