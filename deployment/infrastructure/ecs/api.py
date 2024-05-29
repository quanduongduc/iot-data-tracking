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
    generate_fargate_services,
    cluster,
    repo,
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
api_task_role_arn = role_stack.get_output("api_task_role_arn")
apigw_id = network_stack.get_output("apigw_id")
hosted_zone_id = network_stack.get_output("hosted_zone_id")
apigw_endpoint = network_stack.get_output("apigw_endpoint")

api_image = awsx.ecr.Image(
    f"{prefix}-fastapi-image",
    dockerfile=f"{root_dir_relative}/api/Dockerfile.{stack_name}",
    context=f"{root_dir_relative}/api",
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
    memory="1024",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    task_role_arn=api_task_role_arn,
    execution_role_arn=task_execution_role_arn,
    container_definitions=pulumi.Output.all(
        api_image.image_uri, log_group.name, secret.name
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": f"{prefix}-api-container",
                    "image": args[0],
                    "portMappings": [{"containerPort": 5006}],
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

api_target_group = aws.lb.TargetGroup(
    f"{prefix}-api-tg",
    port=80,
    protocol="HTTP",
    target_type="ip",
    vpc_id=vpc_id,
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        path="/health",
        protocol="HTTP",
        port=5006,
        interval=10,
        timeout=5,
        unhealthy_threshold=2,
        healthy_threshold=2,
    ),
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


api_on_demand_service, api_spot_service = generate_fargate_services(
    prefix=prefix,
    task_definition=api_task_definition.arn,
    cluster=cluster.arn,
    load_balancers=[
        aws.ecs.ServiceLoadBalancerArgs(
            container_name=f"{prefix}-api-container",
            container_port=5006,
            target_group_arn=api_target_group.arn,
        )
    ],
    desired_count=2,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        assign_public_ip=False,
        security_groups=[api_sg_id],
        subnets=[ecs_private_subnet1_id, ecs_private_subnet2_id],
    ),
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
