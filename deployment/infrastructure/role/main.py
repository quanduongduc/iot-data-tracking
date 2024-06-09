import sys
import json
import pulumi
import pulumi_aws as aws

sys.path.append("../../")

from infrastructure.environment import get_arn_template, project_name, account_id


permission_boundary_arn = (
    f"arn:aws:iam::{account_id}:policy/{project_name}-permission-boundary"
)


ecr_read_policy = aws.iam.Policy(
    f"{project_name}-ecr-read-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "ecr:BatchCheckLayerAvailability",
                    ],
                    "Resource": get_arn_template(
                        service="ecr", resource_name=f"repository/{project_name}-*"
                    ),
                },
                {
                    "Effect": "Allow",
                    "Action": ["ecr:GetAuthorizationToken"],
                    "Resource": "*",
                },
            ],
        }
    ),
)

cloudwatch_policy = aws.iam.Policy(
    f"{project_name}-cloudwatch-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:CreateLogGroup",
                    ],
                    "Resource": get_arn_template(
                        service="logs", resource_name=f"log-group:{project_name}-*"
                    ),
                }
            ],
        }
    ),
)

task_execution_role = aws.iam.Role(
    f"{project_name}-task-execution-role",
    assume_role_policy=pulumi.Output.all(
        aws.get_caller_identity().account_id, aws.get_region().name
    ).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                        "Effect": "Allow",
                        "Sid": "",
                    }
                ],
            }
        )
    ),
    managed_policy_arns=[ecr_read_policy.arn, cloudwatch_policy.arn],
    permissions_boundary=permission_boundary_arn,
)

s3_read_policy = aws.iam.Policy(
    f"{project_name}-s3-read-policy",
    description="A policy to allow read access to S3",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:GetObject", "s3:ListBucket", "s3:ListObjectsv2"],
                    "Resource": [
                        get_arn_template(
                            service="s3",
                            resource_name=f"{project_name}-*/*",
                        ),
                        get_arn_template(
                            service="s3",
                            resource_name=f"{project_name}-*",
                        ),
                    ],
                    "Effect": "Allow",
                }
            ],
        }
    ),
)

ecs_registration_policy = aws.iam.Policy(
    f"{project_name}-ecs-registration-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecs:CreateCluster",
                        "ec2:DescribeTags",
                        "ecs:DeregisterContainerInstance",
                        "ecs:DiscoverPollEndpoint",
                        "ecs:Poll",
                        "ecs:RegisterContainerInstance",
                        "ecs:StartTelemetrySession",
                        "ecs:UpdateContainerInstancesState",
                        "ecs:Submit*",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    "Resource": "*",
                }
            ],
        }
    ),
)

secret_manager_policy = aws.iam.Policy(
    f"{project_name}-secret-manager-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetResourcePolicy",
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                        "secretsmanager:ListSecretVersionIds",
                        "secretsmanager:ListSecrets",
                    ],
                    "Resource": get_arn_template(
                        "secretsmanager", f"secret:{project_name}-*"
                    ),
                }
            ],
        }
    ),
)

dynamodb_policy = aws.iam.Policy(
    f"{project_name}-dynamodb-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:UpdateItem",
                    ],
                    "Resource": get_arn_template("dynamodb", f"table/{project_name}-*"),
                }
            ],
        }
    ),
)

sqs_policy = aws.iam.Policy(
    f"{project_name}-sqs-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage"],
                    "Resource": get_arn_template("sqs", f"{project_name}-*"),
                }
            ],
        }
    ),
)

api_task_role = aws.iam.Role(
    f"{project_name}-api-task-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
    managed_policy_arns=[
        s3_read_policy.arn,
        secret_manager_policy.arn,
        cloudwatch_policy.arn,
        ecs_registration_policy.arn,
        dynamodb_policy.arn,
        sqs_policy.arn,
    ],
    permissions_boundary=permission_boundary_arn,
)

data_generator_role = aws.iam.Role(
    f"{project_name}-data-generator-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
    managed_policy_arns=[
        s3_read_policy.arn,
        secret_manager_policy.arn,
        cloudwatch_policy.arn,
        ecs_registration_policy.arn,
        sqs_policy.arn,
    ],
    permissions_boundary=permission_boundary_arn,
)

ecs_update_service_policy = aws.iam.Policy(
    f"{project_name}-ecs-update-service-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["ecs:UpdateService", "ecs:DescribeServices"],
                    "Resource": f"arn:aws:ecs:*:*:service/{project_name}-*",
                }
            ],
        }
    ),
)

put_logs_policy = aws.iam.Policy(
    f"{project_name}-put-logs-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    "Resource": f"arn:aws:logs:*:*:log-group:{project_name}-*",
                }
            ],
        }
    ),
)

spot_shutdown_lambda_role = aws.iam.Role(
    f"{project_name}-spot-shutdown-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
    managed_policy_arns=[
        ecs_update_service_policy.arn,
    ],
    permissions_boundary=permission_boundary_arn,
)

pulumi.export("task_execution_role_arn", task_execution_role.arn)
pulumi.export("api_task_role_arn", api_task_role.arn)
pulumi.export("data_generator_task_role_arn", data_generator_role.arn)
pulumi.export("data_processor_task_role_arn", api_task_role.arn)
pulumi.export("kafka_bridge_task_role_arn", api_task_role.arn)
pulumi.export("spot_shutdown_lambda_role_arn", spot_shutdown_lambda_role.arn)
