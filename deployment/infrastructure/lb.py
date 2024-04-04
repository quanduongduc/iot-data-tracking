import pulumi_aws as aws
import pulumi
from vpc import ecs_private_subnet1, ecs_private_subnet2, alb_sg, vpc
from environment import prefix

alb = aws.lb.LoadBalancer(
    f"{prefix}-alb",
    internal=True,
    subnets=[ecs_private_subnet1, ecs_private_subnet2],
    security_groups=[alb_sg.id],
    load_balancer_type="application",
)

api_target_group = aws.lb.TargetGroup(
    f"{prefix}-api-tg",
    port=80,
    protocol="HTTP",
    vpc_id=vpc.id,
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        path="/health",
        protocol="HTTP",
        port="traffic-port",
        interval=10,
        timeout=5,
        unhealthy_threshold=2,
        healthy_threshold=2,
    ),
    opts=pulumi.ResourceOptions(
        depends_on=[alb],
        replace_on_changes=["arn"],
    ),
)

alb_listener = aws.lb.Listener(
    f"{prefix}-alb-listener",
    load_balancer_arn=alb.arn,
    port=80,
    protocol="HTTP",
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="forward",
            target_group_arn=api_target_group.arn,
        )
    ],
)
