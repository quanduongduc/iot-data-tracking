import pulumi
import pulumi_aws as aws

import sys

sys.path.append("../../")

from infrastructure.network.lb import alb_listener
from infrastructure.network.vpc import (
    ecs_private_subnet1,
    ecs_private_subnet2,
    apigw_vpc_link_sg,
)
from infrastructure.environment import project_name

api_gate_way = aws.apigatewayv2.Api(
    f"{project_name}-api-gateway",
    protocol_type="HTTP",
    route_selection_expression="$request.method $request.path",
)

vpc_link = aws.apigatewayv2.VpcLink(
    f"{project_name}-apigw-vpc-link",
    subnet_ids=[ecs_private_subnet1, ecs_private_subnet2],
    security_group_ids=[apigw_vpc_link_sg.id],
)

integration = aws.apigatewayv2.Integration(
    f"{project_name}-integration",
    api_id=api_gate_way.id,
    integration_type="HTTP_PROXY",
    integration_uri=alb_listener.arn,
    integration_method="ANY",
    connection_type="VPC_LINK",
    connection_id=vpc_link.id,
    payload_format_version="1.0",
    opts=pulumi.ResourceOptions(depends_on=[api_gate_way]),
)

default_route = aws.apigatewayv2.Route(
    f"{project_name}-default-route",
    api_id=api_gate_way.id,
    route_key="$default",
    target=pulumi.Output.concat("integrations/", integration.id),
)

pulumi.export("apigw_id", api_gate_way.id)
pulumi.export("apigw_endpoint", api_gate_way.api_endpoint)
