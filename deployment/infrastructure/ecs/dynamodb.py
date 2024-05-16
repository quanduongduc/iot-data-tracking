import pulumi_aws as aws
from infrastructure.environment import prefix
from infrastructure.ecs.shared_ecs import network_stack

aws_vpc_id = network_stack.get_output("vpc_id")

dynamodb_table = aws.dynamodb.Table(
    f"{prefix}-dynamodb-table",
    attributes=[
        aws.dynamodb.TableAttributeArgs(name="location", type="S"),
        aws.dynamodb.TableAttributeArgs(name="Date", type="S"),
    ],
    hash_key="location",
    range_key="Date",
    read_capacity=100,
    write_capacity=500,
)
