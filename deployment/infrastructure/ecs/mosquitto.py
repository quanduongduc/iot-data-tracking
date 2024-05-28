import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

from infrastructure.environment import prefix, region, root_dir_relative
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
ecs_public_subnet_id = network_stack.get_output("ecs_public_subnet_id")
mqtt_sg_id = network_stack.get_output("mqtt_sg_id")
mqtt_lb_sg_id = network_stack.get_output("mqtt_lb_sg_id")
vpc_id = network_stack.get_output("vpc_id")
task_execution_role_arn = role_stack.get_output("task_execution_role_arn")

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
    memory="2048",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
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
                            "protocol": "tcp",
                            "appProtocol": "http",
                        },
                        {
                            "name": "mqtt-1884-tcp",
                            "containerPort": 1884,
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
    target_type="ip",
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
    target_type="ip",
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

mqtt_on_demand_service, _ = generate_fargate_services(
    need_spot=False,
    prefix=f"{prefix}-mqtt",
    cluster=cluster.arn,
    task_definition=mqtt_task_definition.arn,
    desired_count=2,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        assign_public_ip=False,
        security_groups=[mqtt_sg_id],
        subnets=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    ),
    load_balancers=[
        aws.ecs.ServiceLoadBalancerArgs(
            target_group_arn=mqtt_target_group.arn,
            container_name=f"{prefix}-mqtt-container",
            container_port=1883,
        ),
        aws.ecs.ServiceLoadBalancerArgs(
            target_group_arn=mqtt_ws_target_group.arn,
            container_name=f"{prefix}-mqtt-container",
            container_port=1884,
        ),
    ],
)

MQTT_SOURCE_TOPIC = "weather/data"
MQTT_PROCESSED_TOPIC = "weather/processed"

pulumi.export("mqtt_nlb_dns_name", mosquitto_nlb.dns_name)
