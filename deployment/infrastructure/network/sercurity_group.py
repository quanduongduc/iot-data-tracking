import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix
from infrastructure.network.vpc import (
    vpc,
    ecs_private_subnet1,
    ecs_private_subnet2,
    ecs_public_subnet,
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
    vpc_id=vpc.id,
    description="Allow port for API",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTP from loadbalancer",
            from_port=5006,
            to_port=5006,
            protocol=aws.ec2.ProtocolType.TCP,
            security_groups=[alb_sg.id],
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

mqtt_lb_sg = aws.ec2.SecurityGroup(
    f"{prefix}-mqtt-lb-sg",
    vpc_id=vpc.id,
    description="Allow port for load balancer",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTP from loadbalancer",
            from_port=0,
            to_port=0,
            protocol="-1",
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

mqtt_sg = aws.ec2.SecurityGroup(
    f"{prefix}-mqtt-sg",
    vpc_id=vpc.id,
    description="Allow port for mqtt broker",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="HTTP from loadbalancer",
            from_port=1883,
            to_port=1884,
            protocol=aws.ec2.ProtocolType.TCP,
            security_groups=[mqtt_lb_sg.id],
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

data_generator_sg = aws.ec2.SecurityGroup(
    f"{prefix}-data-generator-sg",
    vpc_id=vpc.id,
    description="Allow data generator to access other services",
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
    from_port=5006,
    to_port=5006,
    protocol=aws.ec2.ProtocolType.TCP,
    security_group_id=alb_sg.id,
    source_security_group_id=api_sg.id,
)

kafka_bridge_sg = aws.ec2.SecurityGroup(
    f"{prefix}-msk-client-sg",
    vpc_id=vpc.id,
    description="Allow access to MSK",
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

data_processor_sg = aws.ec2.SecurityGroup(
    f"{prefix}-data-processor-sg",
    vpc_id=vpc.id,
    description="Allow access to data processor",
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            description="Outbound access to anywhere for any protocol",
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
)

msk_sg = aws.ec2.SecurityGroup(
    f"{prefix}-msk-sg",
    vpc_id=vpc.id,
    description="Allow access to MSK",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="Allow port for msk",
            from_port=9092,
            to_port=9092,
            protocol=aws.ec2.ProtocolType.TCP,
            security_groups=[
                api_sg.id,
                data_generator_sg.id,
                data_processor_sg.id,
                kafka_bridge_sg.id,
            ],
        )
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

cache_sg = aws.ec2.SecurityGroup(
    f"{prefix}-cache-sg",
    vpc_id=vpc.id,
    description="Allow access to ElastiCache",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="Allow port for redis",
            from_port=6379,
            to_port=6379,
            protocol=aws.ec2.ProtocolType.TCP,
            security_groups=[api_sg.id, data_generator_sg.id, data_processor_sg.id],
        )
    ],
)

rds_sg = aws.ec2.SecurityGroup(
    f"{prefix}-rds-sg",
    vpc_id=vpc.id,
    description="Allow access to RDS",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="Allow port for mysql rds",
            from_port=3306,
            to_port=3306,
            protocol=aws.ec2.ProtocolType.TCP,
            security_groups=[api_sg.id, data_generator_sg.id, data_processor_sg.id],
        )
    ],
)

ecr_api_endpoint_sg = aws.ec2.SecurityGroup(
    f"{prefix}-ecr-api-endpoint-sg",
    vpc_id=vpc.id,
    description="Allow traffic from ECR API endpoint",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=[
                ecs_private_subnet1.cidr_block,
                ecs_private_subnet2.cidr_block,
            ],
        )
    ],
)

pulumi.export("ecs_private_subnet1_id", ecs_private_subnet1.id)
pulumi.export("ecs_private_subnet2_id", ecs_private_subnet2.id)
pulumi.export("ecs_public_subnet_id", ecs_public_subnet.id)
pulumi.export("api_sg_id", api_sg.id)
pulumi.export("vpc_id", vpc.id)
pulumi.export("alb_sg_id", alb_sg.id)
pulumi.export("mqtt_lb_sg_id", mqtt_lb_sg.id)
pulumi.export("mqtt_sg_id", mqtt_sg.id)
pulumi.export("data_generator_sg_id", data_generator_sg.id)
pulumi.export("rds_sg_id", rds_sg.id)
pulumi.export("msk_sg_id", msk_sg.id)
pulumi.export("kafka_bridge_sg_id", kafka_bridge_sg.id)
pulumi.export("data_processor_sg_id", data_processor_sg.id)
pulumi.export("cache_sg_id", cache_sg.id)
