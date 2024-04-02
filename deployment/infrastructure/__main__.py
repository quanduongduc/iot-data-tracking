import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
from vpc import (
    ecs_private_subnet1,
    ecs_private_subnet2,
    api_sg,
    vpc,
)
from share_resources import nlb
from environment import prefix, stack_name
from role import task_execution_role, ec2_api_role
from api_gw import deployment
from secrets_manager import secret

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
    memory="256",
    network_mode="bridge",
    requires_compatibilities=["EC2"],
    execution_role_arn=task_execution_role.arn,
    # task_role_arn=ec2_api_role.arn,
    container_definitions=pulumi.Output.all(api_image.image_uri).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-api-container",
                    "image": args[0],
                    "portMappings": [{"containerPort": 5006, "hostPort": 80}],
                    "environment": [
                        {"name": "AWS_SECRET_ID", "value": f"{secret.name}"},
                    ],
                }
            ]
        ),
    ),
)

api_instance_profile = aws.iam.InstanceProfile(
    f"{prefix}-api-instance-profile", role=ec2_api_role
)

ecs_optimized_ami_name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended"
ecs_optimized_ami_id = json.loads(
    aws.ssm.get_parameter(name=ecs_optimized_ami_name).value
)["image_id"]

launch_config = aws.ec2.LaunchConfiguration(
    f"{prefix}-launch-config",
    image_id=ecs_optimized_ami_id,
    instance_type="t2.micro",
    security_groups=[api_sg],
    key_name="test",
    iam_instance_profile=api_instance_profile.arn,
    user_data=pulumi.Output.concat(
        "#!/bin/bash\necho ECS_CLUSTER=", cluster.name, " >> /etc/ecs/ecs.config"
    ),
)


api_target_group = aws.lb.TargetGroup(
    f"{prefix}-api-tg",
    port=80,
    protocol="TCP",
    vpc_id=vpc.id,
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        enabled=True,
        protocol="TCP",
        port="80",
        interval=30,
        timeout=10,
        healthy_threshold=2,
        unhealthy_threshold=2,
    ),
    opts=pulumi.ResourceOptions(
        depends_on=[nlb],
        replace_on_changes=["arn"],
    ),
)

api_auto_scaling_group = aws.autoscaling.Group(
    f"{prefix}-asg",
    launch_configuration=launch_config.id,
    desired_capacity=2,
    health_check_type="ELB",
    min_size=1,
    max_size=3,
    vpc_zone_identifiers=[ecs_private_subnet1.id, ecs_private_subnet2.id],
    target_group_arns=[api_target_group.arn],
    opts=pulumi.ResourceOptions(
        depends_on=[launch_config], replace_on_changes=["launch_configuration"]
    ),
)

capacity_provider = aws.ecs.CapacityProvider(
    f"{prefix}-capacity-provider",
    auto_scaling_group_provider=aws.ecs.CapacityProviderAutoScalingGroupProviderArgs(
        auto_scaling_group_arn=api_auto_scaling_group.arn,
        managed_scaling=aws.ecs.CapacityProviderAutoScalingGroupProviderManagedScalingArgs(
            status="ENABLED",
            target_capacity=10,
        ),
        managed_termination_protection="DISABLED",
    ),
)

cluster_capacity_providers = aws.ecs.ClusterCapacityProviders(
    f"{prefix}-cluster-capacity-providers",
    cluster_name=cluster.name,
    capacity_providers=[capacity_provider.name],
    default_capacity_provider_strategies=[
        aws.ecs.ClusterCapacityProvidersDefaultCapacityProviderStrategyArgs(
            base=1,
            weight=1,
            capacity_provider=capacity_provider.name,
        ),
    ],
)

listener = aws.lb.Listener(
    f"{prefix}-listener",
    load_balancer_arn=nlb.arn,
    port=80,
    protocol="TCP",
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="forward",
            target_group_arn=api_target_group.arn,
        )
    ],
)

api_service = aws.ecs.Service(
    f"{prefix}-api-service",
    cluster=cluster.arn,
    task_definition=api_task_definition.arn,
    launch_type="EC2",
    desired_count=3,
    placement_constraints=[
        aws.ecs.ServicePlacementConstraintArgs(type="distinctInstance"),
    ],
)

pulumi.export("api_gate_way_endpoint", deployment.invoke_url)
