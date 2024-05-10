import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

from infrastructure.environment import prefix, region, root_dir_relative
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
ecs_public_subnet_id = network_stack.get_output("ecs_public_subnet_id")
mqtt_sg_id = network_stack.get_output("mqtt_sg_id")
mqtt_lb_sg_id = network_stack.get_output("mqtt_lb_sg_id")
vpc_id = network_stack.get_output("vpc_id")
task_execution_role_arn = role_stack.get_output("task_execution_role_arn")
ec2_role_name = role_stack.get_output("ec2_api_role_name")

mqtt_image = awsx.ecr.Image(
    f"{prefix}-mqtt-image",
    dockerfile=f"{root_dir_relative}/mosquitto/Dockerfile",
    context=f"{root_dir_relative}/mosquitto",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

mqtt_log_stream = aws.cloudwatch.LogStream(
    f"{prefix}-mqtt-log-stream",
    log_group_name=log_group.name,
)

mqtt_task_definition = aws.ecs.TaskDefinition(
    f"{prefix}-mqtt-task",
    family=f"{prefix}-mqtt-task",
    cpu="1024",
    memory="1024",
    network_mode="bridge",
    requires_compatibilities=["EC2"],
    execution_role_arn=task_execution_role_arn,
    container_definitions=pulumi.Output.all(
        mqtt_image.image_uri, log_group.name, secret.name
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-mqtt-container",
                    "image": args[0],
                    "portMappings": [
                        {
                            "name": "mqtt-1883-tcp",
                            "containerPort": 1883,
                            "hostPort": 1883,
                            "protocol": "tcp",
                            "appProtocol": "http",
                        },
                        {
                            "name": "mqtt-1884-tcp",
                            "containerPort": 1884,
                            "hostPort": 1884,
                            "protocol": "tcp",
                            "appProtocol": "http",
                        },
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": args[1],
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "mqtt",
                        },
                    },
                }
            ]
        ),
    ),
)

instance_profile = aws.iam.InstanceProfile(
    f"{prefix}-mqtt-instance-profile", role=ec2_role_name
)

mqtt_launch_config = aws.ec2.LaunchConfiguration(
    f"{prefix}-mqtt-launch-config",
    image_id=ecs_optimized_ami_id,
    instance_type="t2.small",
    security_groups=[mqtt_sg_id],
    key_name="test",
    iam_instance_profile=instance_profile.arn,
    user_data=pulumi.Output.concat(
        "#!/bin/bash\necho ECS_CLUSTER=", cluster.name, " >> /etc/ecs/ecs.config"
    ),
)

mosquitto_nlb = aws.lb.LoadBalancer(
    f"{prefix}-mqtt-nlb",
    internal=False,
    subnets=[ecs_public_subnet_id],
    security_groups=[mqtt_lb_sg_id],
    load_balancer_type="network",
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

mqtt_ws_target_group = aws.lb.TargetGroup(
    f"{prefix}-ws-tg",
    port=1884,
    protocol="TCP",
    vpc_id=vpc_id,
    stickiness=aws.lb.TargetGroupStickinessArgs(type="source_ip", enabled=True),
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        protocol="TCP",
        port="traffic-port",
        interval=10,
        timeout=5,
        unhealthy_threshold=2,
        healthy_threshold=2,
    ),
)

mqtt_target_group = aws.lb.TargetGroup(
    f"{prefix}-mqtt-tg",
    port=1883,
    protocol="TCP",
    vpc_id=vpc_id,
    stickiness=aws.lb.TargetGroupStickinessArgs(type="source_ip", enabled=True),
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        protocol="TCP",
        port="traffic-port",
        interval=10,
        timeout=5,
        unhealthy_threshold=2,
        healthy_threshold=2,
    ),
)

mqtt_auto_scaling_group = aws.autoscaling.Group(
    f"{prefix}-mqtt-asg",
    launch_configuration=mqtt_launch_config.id,
    desired_capacity=2,
    health_check_type="EC2",
    min_size=2,
    max_size=3,
    vpc_zone_identifiers=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    target_group_arns=[mqtt_ws_target_group.arn, mqtt_target_group.arn],
    opts=pulumi.ResourceOptions(
        depends_on=[mqtt_launch_config],
        replace_on_changes=["launch_configuration"],
    ),
)

mqtt_capacity_provider = aws.ecs.CapacityProvider(
    f"{prefix}-mqtt-capacity-provider",
    auto_scaling_group_provider=aws.ecs.CapacityProviderAutoScalingGroupProviderArgs(
        auto_scaling_group_arn=mqtt_auto_scaling_group.arn,
        managed_scaling=aws.ecs.CapacityProviderAutoScalingGroupProviderManagedScalingArgs(
            status="ENABLED",
            target_capacity=5,
        ),
        managed_termination_protection="DISABLED",
    ),
)

mosquitto_nlb_mqtt_listener = aws.lb.Listener(
    f"{prefix}-mqtt-listener",
    load_balancer_arn=mosquitto_nlb.arn,
    port=1883,
    protocol="TCP",
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="forward", target_group_arn=mqtt_target_group.arn
        )
    ],
    opts=pulumi.ResourceOptions(depends_on=[mosquitto_nlb], delete_before_replace=True),
)

mosquitto_nlb_ws_listener = aws.lb.Listener(
    f"{prefix}-ws-listener",
    load_balancer_arn=mosquitto_nlb.arn,
    port=1884,
    protocol="TCP",
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="forward", target_group_arn=mqtt_ws_target_group.arn
        )
    ],
    opts=pulumi.ResourceOptions(depends_on=[mosquitto_nlb], delete_before_replace=True),
)

mqtt_service = aws.ecs.Service(
    f"{prefix}-mqtt-service",
    cluster=cluster.arn,
    task_definition=mqtt_task_definition.arn,
    desired_count=2,
    capacity_provider_strategies=[
        aws.ecs.ServiceCapacityProviderStrategyArgs(
            capacity_provider=mqtt_capacity_provider.name,
            weight=1,
            base=1,
        )
    ],
)

MQTT_SOURCE_TOPIC = "weather/data"
MQTT_PROCESSED_TOPIC = "weather/processed"
