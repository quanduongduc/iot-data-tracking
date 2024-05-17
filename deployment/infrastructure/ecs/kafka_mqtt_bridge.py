import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

from infrastructure.environment import prefix, region, root_dir_relative, stack_name
from infrastructure.ecs.secrets_manager import secret
from infrastructure.ecs.shared_ecs import (
    cluster,
    repo,
    ecs_optimized_ami_id,
    log_group,
    network_stack,
    role_stack,
)


ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
vpc_id = network_stack.get_output("vpc_id")
task_execution_role_arn = role_stack.get_output("task_execution_role_arn")
ec2_kafka_bridge_role_name = role_stack.get_output("ec2_kafka_bridge_role_name")
kafka_bridge_sg_id = network_stack.get_output("kafka_bridge_sg_id")

kafka_bridge_image = awsx.ecr.Image(
    f"{prefix}-kmb-image",
    dockerfile=f"{root_dir_relative}/kafka-mqtt-bridge/Dockerfile",
    context=f"{root_dir_relative}",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

kafka_bridge_log_stream = aws.cloudwatch.LogStream(
    f"{prefix}-kmb-log-stream",
    log_group_name=log_group.name,
)

kafka_bridge_task_definition = aws.ecs.TaskDefinition(
    f"{prefix}-kmb-task",
    family=f"{prefix}-kmb-task",
    cpu="2048",  # 1 vCPU
    memory="768",  # 0.75 GB of RAM
    network_mode="bridge",
    requires_compatibilities=["EC2"],
    execution_role_arn=task_execution_role_arn,
    container_definitions=pulumi.Output.all(
        kafka_bridge_image.image_uri, log_group.name, secret.name
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-kmb-container",
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
                            "awslogs-stream-prefix": "kmb",
                        },
                    },
                }
            ]
        ),
    ),
)

kafka_bridge_target_group = aws.lb.TargetGroup(
    f"{prefix}-kmb-tg",
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

kafka_bridge_instance_profile = aws.iam.InstanceProfile(
    f"{prefix}-kmb-instance-profile", role=ec2_kafka_bridge_role_name
)

kafka_bridge_launch_config = aws.ec2.LaunchConfiguration(
    f"{prefix}-kmb-launch-config",
    image_id=ecs_optimized_ami_id,
    instance_type="t3.small",
    security_groups=[kafka_bridge_sg_id],
    key_name="test",
    iam_instance_profile=kafka_bridge_instance_profile.arn,
    user_data=pulumi.Output.concat(
        "#!/bin/bash\necho ECS_CLUSTER=", cluster.name, " >> /etc/ecs/ecs.config"
    ),
)

kafka_bridge_auto_scaling_group = aws.autoscaling.Group(
    f"{prefix}-kmb-asg",
    launch_configuration=kafka_bridge_launch_config.id,
    desired_capacity=5,
    health_check_type="EC2",
    min_size=3,
    max_size=6,
    vpc_zone_identifiers=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    target_group_arns=[kafka_bridge_target_group.arn],
    opts=pulumi.ResourceOptions(
        depends_on=[kafka_bridge_launch_config],
        replace_on_changes=["launch_configuration"],
    ),
)

kafka_bridge_capacity_provider = aws.ecs.CapacityProvider(
    f"{prefix}-kmb-capacity-provider",
    auto_scaling_group_provider=aws.ecs.CapacityProviderAutoScalingGroupProviderArgs(
        auto_scaling_group_arn=kafka_bridge_auto_scaling_group.arn,
        managed_scaling=aws.ecs.CapacityProviderAutoScalingGroupProviderManagedScalingArgs(
            status="ENABLED",
            target_capacity=5,
        ),
        managed_termination_protection="DISABLED",
    ),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

kafka_bridge_service = aws.ecs.Service(
    f"{prefix}-kmb-service",
    cluster=cluster.arn,
    task_definition=kafka_bridge_task_definition.arn,
    desired_count=5,
    capacity_provider_strategies=[
        aws.ecs.ServiceCapacityProviderStrategyArgs(
            capacity_provider=kafka_bridge_capacity_provider.name,
            weight=1,
            base=1,
        )
    ],
)
