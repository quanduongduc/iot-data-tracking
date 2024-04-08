import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix


vpc = aws.ec2.Vpc("vpc", cidr_block="10.0.0.0/16")

igw = aws.ec2.InternetGateway(f"{prefix}-igw", vpc_id=vpc.id)
private_route_table = aws.ec2.RouteTable(f"{prefix}-private-route-table", vpc_id=vpc.id)
public_route_table = aws.ec2.RouteTable(f"{prefix}-public-route-table", vpc_id=vpc.id)


ecs_public_subnet = aws.ec2.Subnet(
    f"{prefix}-subnet0",
    vpc_id=vpc.id,
    cidr_block="10.0.3.0/24",
    availability_zone="ap-northeast-1a",
)

ecs_private_subnet1 = aws.ec2.Subnet(
    f"{prefix}-subnet1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="ap-northeast-1c",
)

ecs_private_subnet2 = aws.ec2.Subnet(
    f"{prefix}-subnet2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone="ap-northeast-1a",
)

eip = aws.ec2.Eip(f"{prefix}-eip1")

nat_gateway = aws.ec2.NatGateway(
    f"{prefix}-nat-gateway",
    subnet_id=ecs_public_subnet.id,
    allocation_id=eip.id,
)

nat_route1 = aws.ec2.Route(
    f"{prefix}-nat-route1",
    route_table_id=private_route_table.id,
    destination_cidr_block="0.0.0.0/0",
    nat_gateway_id=nat_gateway.id,
)
private_subnet_route_association1 = aws.ec2.RouteTableAssociation(
    f"{prefix}-private-subnet-route-association1",
    subnet_id=ecs_private_subnet1.id,
    route_table_id=private_route_table.id,
)

private_subnet_route_association2 = aws.ec2.RouteTableAssociation(
    f"{prefix}-private-subnet-route-association2",
    subnet_id=ecs_private_subnet2.id,
    route_table_id=private_route_table.id,
)

public_subnet_route = aws.ec2.Route(
    f"{prefix}-public-subnet-route",
    route_table_id=public_route_table.id,
    destination_cidr_block="0.0.0.0/0",
    gateway_id=igw.id,
)

public_subnet_route_association = aws.ec2.RouteTableAssociation(
    f"{prefix}-public-subnet-route-association",
    route_table_id=public_route_table.id,
    subnet_id=ecs_public_subnet.id,
)

apigw_vpc_link_sg = aws.ec2.SecurityGroup(
    f"{prefix}-apigw-vpc-link-sg",
    vpc_id=vpc.id,
)

alb_sg = aws.ec2.SecurityGroup(
    f"{prefix}-lb-sg",
    name_prefix=prefix,
    vpc_id=vpc.id,
    description="Allow port for load balancer",
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
            protocol=aws.ec2.ProtocolType.TCP,
            security_groups=[alb_sg.id],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            description="SSH from anywhere",
            from_port=22,
            to_port=22,
            protocol=aws.ec2.ProtocolType.TCP,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            description="Outbound access to anywhere for any protocol",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
)

apigw_vpc_link_sg_egress = aws.ec2.SecurityGroupRule(
    f"{prefix}-apigw-vpc-link-sg-ingress",
    type="egress",
    from_port=80,
    to_port=80,
    protocol=aws.ec2.ProtocolType.TCP,
    security_group_id=apigw_vpc_link_sg.id,
    source_security_group_id=alb_sg.id,
)

alb_sg_ingress = aws.ec2.SecurityGroupRule(
    f"{prefix}-lb-sg-ingress",
    type="ingress",
    from_port=80,
    to_port=80,
    protocol=aws.ec2.ProtocolType.TCP,
    security_group_id=alb_sg.id,
    source_security_group_id=apigw_vpc_link_sg.id,
)

alb_sg_egrees = aws.ec2.SecurityGroupRule(
    f"{prefix}-lb-sg-egress",
    type="egress",
    from_port=80,
    to_port=80,
    protocol=aws.ec2.ProtocolType.TCP,
    security_group_id=alb_sg.id,
    source_security_group_id=api_sg.id,
)

pulumi.export("ecs_private_subnet1_id", ecs_private_subnet1.id)
pulumi.export("ecs_private_subnet2_id", ecs_private_subnet2.id)
pulumi.export("api_sg_id", api_sg.id)
pulumi.export("vpc_id", vpc.id)
pulumi.export("alb_sg_id", alb_sg.id)
