import pulumi_aws as aws
from naming import prefix

vpc = aws.ec2.Vpc("vpc", cidr_block="10.0.0.0/16")

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

api_sg = aws.ec2.SecurityGroup(
    f"{prefix}-api-sg",
    name_prefix=prefix,
    vpc_id=vpc.id,
    description="Allow port 80",
    ingress=[
        {
            "description": "HTTP",
            "from_port": 80,
            "to_port": 80,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        }
    ],
)
