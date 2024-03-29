import pulumi_aws as aws
from environment import prefix


vpc = aws.ec2.Vpc("vpc", cidr_block="10.0.0.0/16")

igw = aws.ec2.InternetGateway(f"{prefix}-igw", vpc_id=vpc.id)
route_table = aws.ec2.RouteTable(f"{prefix}-route-table", vpc_id=vpc.id)


ecs_subnet1 = aws.ec2.Subnet(
    f"{prefix}-subnet1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="ap-northeast-1c",
)

ecs_subnet2 = aws.ec2.Subnet(
    f"{prefix}-subnet2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone="ap-northeast-1a",
)

route_table_association1 = aws.ec2.RouteTableAssociation(
    f"{prefix}-route-table-association1",
    subnet_id=ecs_subnet1.id,
    route_table_id=route_table.id,
)

route_table_association2 = aws.ec2.RouteTableAssociation(
    f"{prefix}-route-table-association2",
    subnet_id=ecs_subnet2.id,
    route_table_id=route_table.id,
)

alb = aws.lb.LoadBalancer(
    f"{prefix}-alb",
    subnets=[ecs_subnet1, ecs_subnet2],
    load_balancer_type="network",
)

apigw_link_lb = aws.apigateway.VpcLink(
    f"{prefix}-vpc-link",
    target_arn=alb.arn,
)
lb_sg = aws.ec2.SecurityGroup(
    f"{prefix}-lb-sg",
    name_prefix=prefix,
    vpc_id=vpc.id,
    description="Allow port for load balancer",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTP from API Gateway via VPC Link",
            from_port=80,
            to_port=80,
            protocol="tcp",
            security_groups=[apigw_link_lb.id],
        )
    ],
)

api_sg = aws.ec2.SecurityGroup(
    f"{prefix}-api-sg",
    name_prefix=prefix,
    vpc_id=vpc.id,
    description="Allow port for API",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTP from loadbalancer",
            from_port=80,
            to_port=80,
            protocol="tcp",
            security_groups=[lb_sg.id],
        )
    ],
)
