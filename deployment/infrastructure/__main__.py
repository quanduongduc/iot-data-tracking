import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
from vpc import vpc, ecs_subnet1, ecs_subnet2, api_sg
from naming import prefix


cluster = aws.ecs.Cluster(f"{prefix}-cluster")

repo = aws.ecr.Repository(
    f"{prefix}-repo",
    opts=pulumi.ResourceOptions(additional_secret_outputs=["repository_url"]),
)

api_image = awsx.ecr.Image(
    f"{prefix}-fastapi-image",
    dockerfile="../Dockerfile",
    context="../..",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

# image = awsx.ecr.Image(
#     f"{prefix}-fastapi_image",
#     dockerfile="../Dockerfile",
#     context="../..",
#     repository_url=repo.repository_url,
#     platform="linux/amd64",
#     opts=pulumi.ResourceOptions(additional_secret_outputs=["name, repository_url"]),
# )

# api_task_definition = aws.ecs.TaskDefinition(
#     "api-task",
#     family="api-task",
#     cpu="256",
#     memory="512",
#     network_mode="awsvpc",
#     requires_compatibilities=["EC2", "FARGATE"],
#     execution_role_arn=awsx.ecs.TaskExecutionRole.get().arn,
#     container_definitions=pulumi.Output.all(image.repository_url, image.name).apply(
#         lambda args: f"""[
#             {{
#                 "name": "api-container",
#                 "image": "{args[0]}:{args[1]}",
#                 "portMappings": [
#                     {{
#                         "containerPort": 80,
#                         "hostPort": 80
#                     }}
#                 ]
#             }}
#         ]"""
#     ),
# )

# api_service = aws.ecs.Service(
#     "api_service",
#     cluster=cluster.arn,
#     task_definition=api_task_definition.arn,
#     launch_type="EC2",
#     network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
#         subnets=[
#             subnet1.id,
#             subnet2.id,
#         ],
#         assign_public_ip=False,
#         security_groups=[
#             api_sg.id,
#         ],
#     ),
#     desired_count=1,
# )

# pulumi.export("service_name", api_service.name)
