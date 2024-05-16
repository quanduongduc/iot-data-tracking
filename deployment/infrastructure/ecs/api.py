import sys

sys.path.append("../../")

from infrastructure.utils import get_primary_domain
import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx

from infrastructure.environment import (
    prefix,
    region,
    root_dir_relative,
    stack_name,
)
from infrastructure.ecs.secrets_manager import secret
from infrastructure.ecs.shared_ecs import (
    cluster,
    repo,
    ecs_optimized_ami_id,
    log_group,
    network_stack,
    role_stack,
)

ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
api_sg_id = network_stack.get_output("api_sg_id")
vpc_id = network_stack.get_output("vpc_id")
alb_listener_arn = network_stack.get_output("alb_listener_arn")
task_execution_role_arn = role_stack.get_output("task_execution_role_arn")
ec2_api_role_name = role_stack.get_output("ec2_api_role_name")
apigw_id = network_stack.get_output("apigw_id")
hosted_zone_id = network_stack.get_output("hosted_zone_id")
apigw_endpoint = network_stack.get_output("apigw_endpoint")

api_image = awsx.ecr.Image(
    f"{prefix}-fastapi-image",
    dockerfile=f"{root_dir_relative}/api/Dockerfile.{stack_name}",
    context=f"{root_dir_relative}",
    repository_url=repo.repository_url,
    platform="linux/amd64",
)

api_log_stream = aws.cloudwatch.LogStream(
    f"{prefix}-api-log-stream",
    log_group_name=log_group.name,
)

api_task_definition = aws.ecs.TaskDefinition(
    f"{prefix}-api-task",
    family=f"{prefix}-api-task",
    cpu="512",
    memory="512",
    network_mode="bridge",
    requires_compatibilities=["EC2"],
    execution_role_arn=task_execution_role_arn,
    container_definitions=pulumi.Output.all(
        api_image.image_uri, log_group.name, secret.name
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-api-container",
                    "image": args[0],
                    "portMappings": [{"containerPort": 5006, "hostPort": 80}],
                    "environment": [
                        {"name": "ENVIRONMENT", "value": f"{stack_name.upper()}"},
                        {"name": "AWS_SECRET_ID", "value": f"{args[2]}"},
                        {"name": "AWS_DEFAULT_REGION", "value": f"{region}"},
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": args[1],
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "api",
                        },
                    },
                }
            ]
        ),
    ),
)

api_instance_profile = aws.iam.InstanceProfile(
    f"{prefix}-api-instance-profile", role=ec2_api_role_name
)

api_launch_config = aws.ec2.LaunchConfiguration(
    f"{prefix}-api-launch-config",
    image_id=ecs_optimized_ami_id,
    instance_type="t3.small",
    security_groups=[api_sg_id],
    key_name="test",
    iam_instance_profile=api_instance_profile.arn,
    user_data=pulumi.Output.concat(
        "#!/bin/bash\necho ECS_CLUSTER=", cluster.name, " >> /etc/ecs/ecs.config"
    ),
)

api_target_group = aws.lb.TargetGroup(
    f"{prefix}-api-tg",
    port=80,
    protocol="HTTP",
    vpc_id=vpc_id,
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        path="/health",
        protocol="HTTP",
        port="traffic-port",
        interval=10,
        timeout=5,
        unhealthy_threshold=2,
        healthy_threshold=2,
    ),
)

api_auto_scaling_group = aws.autoscaling.Group(
    f"{prefix}-api-asg",
    launch_configuration=api_launch_config.id,
    desired_capacity=4,
    health_check_type="ELB",
    min_size=3,
    max_size=5,
    vpc_zone_identifiers=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    target_group_arns=[api_target_group.arn],
    opts=pulumi.ResourceOptions(
        depends_on=[api_launch_config], replace_on_changes=["launch_configuration"]
    ),
)

api_capacity_provider = aws.ecs.CapacityProvider(
    f"{prefix}-api-capacity-provider",
    auto_scaling_group_provider=aws.ecs.CapacityProviderAutoScalingGroupProviderArgs(
        auto_scaling_group_arn=api_auto_scaling_group.arn,
        managed_scaling=aws.ecs.CapacityProviderAutoScalingGroupProviderManagedScalingArgs(
            status="ENABLED",
            target_capacity=5,
        ),
        managed_termination_protection="DISABLED",
    ),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

api_service = aws.ecs.Service(
    f"{prefix}-api-service",
    cluster=cluster.arn,
    task_definition=api_task_definition.arn,
    desired_count=5,
    capacity_provider_strategies=[
        aws.ecs.ServiceCapacityProviderStrategyArgs(
            capacity_provider=api_capacity_provider.name,
            weight=1,
            base=1,
        )
    ],
    placement_constraints=[
        aws.ecs.ServicePlacementConstraintArgs(type="distinctInstance"),
    ],
    opts=pulumi.ResourceOptions(
        delete_before_replace=True,
    ),
)

config = pulumi.Config()
domain_name = config.require_object("domain_name").get("value")
primary_domain_name = get_primary_domain(domain_name)

# certificate = aws.acm.get_certificate(
#     domain=primary_domain_name,
#     statuses=["ISSUED"],
# )


deployment = aws.apigatewayv2.Deployment(
    f"{prefix}-deployment",
    api_id=apigw_id,
)

apigw_stage = aws.apigatewayv2.Stage(
    f"{prefix}-apigw-stage",
    api_id=apigw_id,
    deployment_id=deployment.id,
    auto_deploy=True,
    name=stack_name,
    opts=pulumi.ResourceOptions(delete_before_replace=False),
)


aws.lb.ListenerRule(
    f"{prefix}-api-listener-rule",
    actions=[
        aws.lb.ListenerRuleActionArgs(
            type="forward",
            target_group_arn=api_target_group.arn,
        )
    ],
    priority=10,
    conditions=[
        aws.lb.ListenerRuleConditionArgs(
            path_pattern=aws.lb.ListenerRuleConditionPathPatternArgs(
                values=[f"/{stack_name}/*"],
            )
        )
    ],
    listener_arn=alb_listener_arn,
)


# apigw_domain_name = aws.apigatewayv2.DomainName(
#     f"{prefix}-apigw-domain-name",
#     domain_name=domain_name,
#     domain_name_configuration=aws.apigatewayv2.DomainNameDomainNameConfigurationArgs(
#         certificate_arn=certificate.arn,
#         endpoint_type="REGIONAL",
#         security_policy="TLS_1_2",
#     ),
#     opts=pulumi.ResourceOptions(delete_before_replace=True),
# )

# base_path_mapping_v2 = aws.apigatewayv2.ApiMapping(
#     f"{prefix}-base-path-mapping",
#     api_id=apigw_id,
#     stage=apigw_stage.name,
#     domain_name=apigw_domain_name.domain_name,
#     opts=pulumi.ResourceOptions(
#         replace_on_changes=["stage"], delete_before_replace=True
#     ),
# )

# dns_record = aws.route53.Record(
#     f"{prefix}-apiGatewayDnsRecord",
#     zone_id=hosted_zone_id,
#     name=apigw_domain_name.domain_name,
#     type="A",
#     aliases=[
#         aws.route53.RecordAliasArgs(
#             name=apigw_domain_name.domain_name_configuration.target_domain_name,
#             zone_id=apigw_domain_name.domain_name_configuration.hosted_zone_id,
#             evaluate_target_health=True,
#         )
#     ],
# )


pulumi.export(f"{stack_name}_endpoint", apigw_stage.invoke_url)
