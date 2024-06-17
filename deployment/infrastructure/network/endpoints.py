from typing import List
import pulumi_aws as aws
from infrastructure.network.vpc import vpc, ecs_private_subnet1, ecs_private_subnet2
from infrastructure.network.sercurity_group import ecr_api_endpoint_sg
from infrastructure.environment import prefix


class VpcEndpointType:
    Interface = "Interface"
    Gateway = "Gateway"


def create_vpc_endpoint(
    service: str,
    vpc: aws.ec2.Vpc,
    prefix: str,
    vpc_endpoint_type: VpcEndpointType,
    security_group_ids: List[str],
    subnet_ids: List[str],
) -> aws.ec2.VpcEndpoint:
    if vpc_endpoint_type == VpcEndpointType.Interface:
        return aws.ec2.VpcEndpoint(
            f"{prefix}-{service}-vpc-endpoint",
            vpc_id=vpc.id,
            service_name=service,
            vpc_endpoint_type=vpc_endpoint_type,
            private_dns_enabled=True,
            security_group_ids=security_group_ids,
            subnet_ids=subnet_ids,
        )
    return aws.ec2.VpcEndpoint(
        f"{prefix}-{service}-vpc-endpoint",
        vpc_id=vpc.id,
        service_name=service,
        vpc_endpoint_type=vpc_endpoint_type,
    )


subnet_ids = [ecs_private_subnet1.id, ecs_private_subnet2.id]
ecr_endpoint_sg_ids = [ecr_api_endpoint_sg.id]

s3_endpoint = create_vpc_endpoint("s3", vpc, prefix, VpcEndpointType.Gateway, [], [])
dynamodb_endpoint = create_vpc_endpoint(
    "dynamodb", vpc, prefix, VpcEndpointType.Gateway, [], []
)

ecr_api_endpoint = create_vpc_endpoint(
    "ecrApi", vpc, prefix, VpcEndpointType.Interface, subnet_ids, ecr_endpoint_sg_ids
)
ecr_docker_endpoint = create_vpc_endpoint(
    "ecrDocker", vpc, prefix, VpcEndpointType.Interface, subnet_ids, ecr_endpoint_sg_ids
)
cloudwatch_logs_endpoint = create_vpc_endpoint(
    "cloudwatchLogs", vpc, prefix, VpcEndpointType.Interface, subnet_ids, []
)
