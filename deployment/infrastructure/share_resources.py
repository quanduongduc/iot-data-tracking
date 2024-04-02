import pulumi_aws as aws
from vpc import (
    ecs_private_subnet1,
    ecs_private_subnet2,
    lb_sg,
)
from environment import prefix

nlb = aws.lb.LoadBalancer(
    f"{prefix}-nlb",
    internal=True,
    subnets=[ecs_private_subnet1, ecs_private_subnet2],
    security_groups=[lb_sg.id],
    load_balancer_type="network",
)
