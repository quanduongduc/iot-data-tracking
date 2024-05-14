import pulumi_aws as aws

from infrastructure.ecs.shared_ecs import (
    network_stack,
    role_stack,
)

from infrastructure.environment import prefix

ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
cache_sg_id = network_stack.get_output("cache_sg_id")
ec2_api_role_name = role_stack.get_output("ec2_api_role_name")

cache_subnet_group = aws.elasticache.SubnetGroup(
    f"{prefix}-cache-subnet-group",
    subnet_ids=[ecs_private_subnet1_id, ecs_private_subnet2_id],
)

elasticache_cluster = aws.elasticache.Cluster(
    f"{prefix}-elasticache-cluster",
    engine="redis",
    node_type="cache.t3.medium",
    num_cache_nodes=1,
    parameter_group_name="default.redis7",
    engine_version="7.0",
    subnet_group_name=cache_subnet_group.name,
    security_group_ids=[cache_sg_id],
)
