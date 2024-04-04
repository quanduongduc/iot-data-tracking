import pulumi
import pulumi_aws as aws
from lb import alb_listener
from environment import prefix, stack_name

api_gate_way = aws.apigatewayv2.Api(
    f"{prefix}-api-gateway",
    protocol_type="HTTP",
    route_selection_expression="$request.method $request.path",
)

integration = aws.apigatewayv2.Integration(
    f"{prefix}-integration",
    api_id=api_gate_way.id,
    integration_type="HTTP_PROXY",
    integration_uri=alb_listener.arn,
    integration_method="ANY",
    payload_format_version="1.0",
    opts=pulumi.ResourceOptions(depends_on=[api_gate_way]),
)


default_route = aws.apigatewayv2.Route(
    f"{prefix}-default-route",
    api_id=api_gate_way.id,
    route_key="$default",
    target=pulumi.Output.concat("integrations/", integration.id),
)

deployment = aws.apigatewayv2.Deployment(
    f"{prefix}-deployment",
    api_id=api_gate_way.id,
    opts=pulumi.ResourceOptions(depends_on=[default_route]),
)

stage = aws.apigatewayv2.Stage(
    f"{prefix}-http_api_stage",
    api_id=api_gate_way.id,
    deployment_id=deployment.id,
    name=stack_name,
    auto_deploy=True,
)
