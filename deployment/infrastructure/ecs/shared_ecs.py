import json
import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix, ref_prefix

network_stack = pulumi.StackReference(f"{ref_prefix}/network")
role_stack = pulumi.StackReference(f"{ref_prefix}/role")

cluster = aws.ecs.Cluster(f"{prefix}-cluster")
repo = aws.ecr.Repository(
    f"{prefix}-repo",
    force_delete=True,
    opts=pulumi.ResourceOptions(additional_secret_outputs=["repository_url"]),
)

log_group = aws.cloudwatch.LogGroup(
    f"{prefix}-log",
    retention_in_days=7,
)

ecs_optimized_ami_name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended"

ecs_optimized_ami_id = json.loads(
    aws.ssm.get_parameter(name=ecs_optimized_ami_name).value
)["image_id"]
