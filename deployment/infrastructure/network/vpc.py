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

# eip = aws.ec2.Eip(f"{prefix}-eip1")

# nat_gateway = aws.ec2.NatGateway(
#     f"{prefix}-nat-gateway",
#     subnet_id=ecs_public_subnet.id,
#     allocation_id=eip.id,
# )

# nat_route1 = aws.ec2.Route(
#     f"{prefix}-nat-route1",
#     route_table_id=private_route_table.id,
#     destination_cidr_block="0.0.0.0/0",
#     nat_gateway_id=nat_gateway.id,
# )
