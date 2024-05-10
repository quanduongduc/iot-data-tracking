import pulumi
import pulumi_aws as aws
from infrastructure.ecs.shared_ecs import role_stack, network_stack
from infrastructure.environment import prefix
import pulumi_random as random


ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
rds_sg_id = network_stack.get_output("rds_sg_id")

rds_subnet_group = aws.rds.SubnetGroup(
    f"{prefix}-rds-subnet-group",
    subnet_ids=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

db_password = random.RandomPassword(
    f"{prefix}-db-password", special=False, length=30
).result

rds_instance = aws.rds.Instance(
    f"{prefix}-rds-instance",
    allocated_storage=20,
    engine="mysql",
    engine_version="8.0",
    instance_class=aws.rds.InstanceType.T3_SMALL,
    db_name="weathertracking",
    username="db_user",
    password=db_password,
    db_subnet_group_name=rds_subnet_group.name,
    skip_final_snapshot=True,
    vpc_security_group_ids=[rds_sg_id],
    publicly_accessible=False,
)
