import pulumi
import pulumi_aws as aws
from vpc import (
    nlb,
)
from environment import prefix, stack_name

apigw_link_lb = aws.apigateway.VpcLink(
    f"{prefix}-vpc-link",
    target_arn=nlb.arn,
)

api_gate_way = aws.apigateway.RestApi(
    f"{prefix}-api-gateway",
)

resource = aws.apigateway.Resource(
    f"{prefix}-resource",
    rest_api=api_gate_way.id,
    parent_id=api_gate_way.root_resource_id,
    path_part="{proxy+}",
)

method = aws.apigateway.Method(
    f"{prefix}-method",
    rest_api=api_gate_way.id,
    resource_id=resource.id,
    http_method="ANY",
    authorization="NONE",
)

api_gate_way_integration = aws.apigateway.Integration(
    f"{prefix}-integration",
    rest_api=api_gate_way.id,
    resource_id=resource.id,
    http_method=method.http_method,
    type="HTTP_PROXY",
    integration_http_method="GET",
    uri=nlb.dns_name.apply(lambda dns: f"http://{dns}"),
    connection_type="VPC_LINK",
    connection_id=apigw_link_lb.id,
)


deployment = aws.apigateway.Deployment(
    f"{prefix}-deployment",
    rest_api=api_gate_way.id,
    stage_name=stack_name,
    opts=pulumi.ResourceOptions(depends_on=[api_gate_way_integration]),
)
