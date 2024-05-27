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
    memory="768",  # 0.75 GB of RAM
    network_mode="bridge",
    requires_compatibilities=["EC2"],
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

data_processor_target_group = aws.lb.TargetGroup(
    f"{prefix}-dp-tg",
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

data_processor_instance_profile = aws.iam.InstanceProfile(
    f"{prefix}-dp-instance-profile", role=ec2_data_processor_role_name
)

data_processor_launch_config = aws.ec2.LaunchConfiguration(
    f"{prefix}-dp-launch-config",
    image_id=ecs_optimized_ami_id,
    instance_type="t3.small",
    security_groups=[data_processor_sg_id],
    key_name="test",
    iam_instance_profile=data_processor_instance_profile.arn,
    user_data=pulumi.Output.concat(
        "#!/bin/bash\necho ECS_CLUSTER=", cluster.name, " >> /etc/ecs/ecs.config"
    ),
)

data_processor_auto_scaling_group = aws.autoscaling.Group(
    f"{prefix}-dp-asg",
    launch_configuration=data_processor_launch_config.id,
    desired_capacity=5,
    health_check_type="EC2",
    min_size=4,
    max_size=6,
    vpc_zone_identifiers=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    target_group_arns=[data_processor_target_group.arn],
    opts=pulumi.ResourceOptions(
        depends_on=[data_processor_launch_config],
        replace_on_changes=["launch_configuration"],
    ),
)

data_processor_capacity_provider = aws.ecs.CapacityProvider(
    f"{prefix}-dp-capacity-provider",
    auto_scaling_group_provider=aws.ecs.CapacityProviderAutoScalingGroupProviderArgs(
        auto_scaling_group_arn=data_processor_auto_scaling_group.arn,
        managed_scaling=aws.ecs.CapacityProviderAutoScalingGroupProviderManagedScalingArgs(
            status="ENABLED",
            target_capacity=5,
        ),
        managed_termination_protection="DISABLED",
    ),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

data_processor_service = aws.ecs.Service(
    f"{prefix}-dp-service",
    cluster=cluster.arn,
    task_definition=data_processor_task_definition.arn,
    desired_count=10,
    capacity_provider_strategies=[
        aws.ecs.ServiceCapacityProviderStrategyArgs(
            capacity_provider=data_processor_capacity_provider.name,
            weight=1,
            base=1,
        )
    ],
)
