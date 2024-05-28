import pulumi
import pulumi_aws as aws
from infrastructure.environment import project_name
from infrastructure.network.vpc import (
    ecs_private_subnet1,
    ecs_private_subnet2,
    alb_sg,
)

alb = aws.lb.LoadBalancer(
    f"{project_name}-alb",
    internal=True,
    subnets=[ecs_private_subnet1, ecs_private_subnet2],
    security_groups=[alb_sg.id],
    load_balancer_type="application",
)


alb_listener = aws.lb.Listener(
    f"{project_name}-alb-listener",
    load_balancer_arn=alb.arn,
    port=80,
    protocol="HTTP",
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="fixed-response",
            fixed_response=aws.lb.ListenerDefaultActionFixedResponseArgs(
                content_type="text/plain",
                message_body="Service is unavailable",
                status_code="503",
            ),
        )
    ],
)

pulumi.export("alb_listener_arn", alb_listener.arn)
