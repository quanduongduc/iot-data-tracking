import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
from vpc import ecs_subnet1, ecs_subnet2, api_sg, vpc
from environment import prefix, stack_name
from role import task_execution_role, ec2_api_role

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

api_instance_profile = aws.iam.InstanceProfile(
    f"{prefix}-api-instance-profile", role=ec2_api_role
)

ecs_optimized_ami_name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended"
ami_id = aws.ssm.get_parameter(name=ecs_optimized_ami_name)

launch_config = aws.ecs.LaunchConfiguration(
    f"{prefix}-launch-config",
    image_id=ami_id,  
    instance_type="t2.micro",
    iam_instance_profile=api_instance_profile,
    security_groups=[api_sg],
)

api_auto_scaling_group = aws.autoscaling.Group(
    f"{prefix}-asg",
    launch_configuration=launch_config.id,
    desired_capacity=2,
    min_size=1,
    max_size=3,
    vpc_zone_identifier=[ecs_subnet1, ecs_subnet2]
)

api_target_group = aws.lb.TargetGroup(
    f"{prefix}-api-target-group",
    port=80,
    protocol="HTTP",
    vpc_id=vpc.id,
)

alb = aws.lb.LoadBalancer(
    f"{prefix}-alb",
    subnets=[ecs_subnet1, ecs_subnet2],
    load_balancer_type="network",
    security_groups=[sg_id],
)

listener = aws.lb.Listener(
    f"{prefix}-listener",
    load_balancer_arn=alb.arn,
    port=80,
    default_actions=[
        {
            "type": "forward",
            "target_group_arn": api_target_group.arn,
        }
    ],
)

vpc_link = aws.apigateway.VpcLink(
    f"{prefix}-vpc-link",
    target_arns=[alb.arn],
)

api_gate_way = aws.apigateway.RestApi(
    f"{prefix}-api-gateway",
)

resource = aws.apigateway.Resource(
    f"{prefix}-resource",
    rest_api=api_gate_way.id,
    parent_id=api_gate_way.root_resource_id,
    path_part="{proxy+}",
)

method = aws.apigateway.Method(
    f"{prefix}-method",
    rest_api=api_gate_way.id,
    resource_id=resource.id,
    http_method="ANY",
    authorization="NONE",
)

api_gate_way_integration = aws.apigateway.Integration(
    f"{prefix}-integration",
    rest_api=api_gate_way.id,
    resource_id=resource.id,
    http_method=method.http_method,
    type="HTTP_PROXY",
    integration_http_method="ANY",
    uri=f"http://{alb.dns_name}/{resource.path_part}",
    connection_type="VPC_LINK",
    connection_id=vpc_link.id,
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
