import sys

sys.path.append("../../")

import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

from infrastructure.environment import prefix, stack_name, region, ref_prefix
from infrastructure.ecs.secrets_manager import secret

network_stack = pulumi.StackReference(f"{ref_prefix}/network")
role_stack = pulumi.StackReference(f"{ref_prefix}/role")

ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
api_sg_id = network_stack.get_output("api_sg_id")
vpc_id = network_stack.get_output("vpc_id")
alb_listener_arn = network_stack.get_output("alb_listener_arn")
task_execution_role_arn = role_stack.get_output("task_execution_role_arn")
ec2_api_role_name = role_stack.get_output("ec2_api_role_name")
endpoint_url = network_stack.get_output("endpoint")

cluster = aws.ecs.Cluster(f"{prefix}-cluster")
repo = aws.ecr.Repository(
    f"{prefix}-repo",
    force_delete=True,
    opts=pulumi.ResourceOptions(additional_secret_outputs=["repository_url"]),
)

api_image = awsx.ecr.Image(
    f"{prefix}-fastapi-image",
    dockerfile=f"../../Dockerfile.{stack_name}",
    context="../../..",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

log_group = aws.cloudwatch.LogGroup(
    f"{prefix}-log",
    retention_in_days=7,
)
api_log_stream = aws.cloudwatch.LogStream(
    f"{prefix}-api-log-stream",
    log_group_name=log_group.name,
)

api_task_definition = aws.ecs.TaskDefinition(
    f"{prefix}-api-task",
    family=f"{prefix}-api-task",
    cpu="256",
    memory="256",
    network_mode="bridge",
    requires_compatibilities=["EC2"],
    execution_role_arn=task_execution_role_arn,
    container_definitions=pulumi.Output.all(
        api_image.image_uri, log_group.name, secret.name
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-api-container",
                    "image": args[0],
                    "portMappings": [{"containerPort": 5006, "hostPort": 80}],
                    "environment": [
                        {"name": "AWS_SECRET_ID", "value": f"{args[2]}"},
                        {"name": "AWS_DEFAULT_REGION", "value": f"{region}"},
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": args[1],
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "api",
                        },
                    },
                }
            ]
        ),
    ),
)

api_instance_profile = aws.iam.InstanceProfile(
    f"{prefix}-api-instance-profile", role=ec2_api_role_name
)

ecs_optimized_ami_name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended"
ecs_optimized_ami_id = json.loads(
    aws.ssm.get_parameter(name=ecs_optimized_ami_name).value
)["image_id"]

launch_config = aws.ec2.LaunchConfiguration(
    f"{prefix}-launch-config",
    image_id=ecs_optimized_ami_id,
    instance_type="t2.micro",
    security_groups=[api_sg_id],
    key_name="test",
    iam_instance_profile=api_instance_profile.arn,
    user_data=pulumi.Output.concat(
        "#!/bin/bash\necho ECS_CLUSTER=", cluster.name, " >> /etc/ecs/ecs.config"
    ),
)

api_target_group = aws.lb.TargetGroup(
    f"{prefix}-api-tg",
    port=80,
    protocol="HTTP",
    vpc_id=vpc_id,
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        path="/health",
        protocol="HTTP",
        port="traffic-port",
        interval=10,
        timeout=5,
        unhealthy_threshold=2,
        healthy_threshold=2,
    ),
)

api_auto_scaling_group = aws.autoscaling.Group(
    f"{prefix}-asg",
    launch_configuration=launch_config.id,
    desired_capacity=2,
    health_check_type="ELB",
    min_size=1,
    max_size=3,
    vpc_zone_identifiers=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    target_group_arns=[api_target_group.arn],
    opts=pulumi.ResourceOptions(
        depends_on=[launch_config], replace_on_changes=["launch_configuration"]
    ),
)


aws.lb.ListenerRule(
    f"{prefix}-api-listener-rule",
    actions=[
        aws.lb.ListenerRuleActionArgs(
            type="forward", target_group_arn=api_target_group.arn
        )
    ],
    conditions=[
        aws.lb.ListenerRuleConditionArgs(
            host_header=aws.lb.ListenerRuleConditionHostHeaderArgs(
                values=[
                    "43bgcy1zak.execute-api.ap-northeast-1.amazonaws.com"
                ]  # just for testing
            )
        )
    ],
    listener_arn=alb_listener_arn,
    priority=10,
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

pulumi.export("secret_name", secret.name)
