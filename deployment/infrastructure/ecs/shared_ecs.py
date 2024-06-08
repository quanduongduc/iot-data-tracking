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


def generate_fargate_services(prefix: str, need_spot=True, *args, **kwargs) -> tuple[aws.ecs.Service, aws.ecs.Service]:
    desired_count = kwargs.pop("desired_count", None)
    if desired_count is None:
        raise ValueError("desired_count must be provided")

    on_demand_service = aws.ecs.Service(
        f"{prefix}-service",
        capacity_provider_strategies=[
            aws.ecs.ServiceCapacityProviderStrategyArgs(
                capacity_provider="FARGATE",
                weight=1,
            )
        ],
        desired_count=0 if need_spot else desired_count,
        **kwargs,
    )
    
    if need_spot:
        spot_service = aws.ecs.Service(
            f"{prefix}-spot-service",
            capacity_provider_strategies=[
                aws.ecs.ServiceCapacityProviderStrategyArgs(
                    capacity_provider="FARGATE_SPOT",
                    weight=1,
                )
            ],
            desired_count=desired_count,
            **kwargs,
        )

        return on_demand_service, spot_service
    return on_demand_service, None
