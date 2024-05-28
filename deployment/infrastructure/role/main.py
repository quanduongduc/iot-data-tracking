import sys

sys.path.append("../../")

import json
import pulumi
import pulumi_aws as aws
from infrastructure.environment import get_arn_template, project_name

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
    ],
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
    ],
)

msk_policy = aws.iam.Policy(
    f"{project_name}-msk-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "kafka-cluster:Connect",
                        "kafka-cluster:DescribeCluster",
                    ],
                    "Resource": [
                        get_arn_template("kafka", f"cluster/{project_name}-*")
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kafka-cluster:WriteData",
                        "kafka-cluster:DescribeTopic",
                    ],
                    "Resource": [get_arn_template("kafka", f"topic/{project_name}-*")],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kafka-cluster:CreateTopic",
                        "kafka-cluster:WriteData",
                        "kafka-cluster:ReadData",
                        "kafka-cluster:DescribeTopic",
                    ],
                    "Resource": [get_arn_template("kafka", f"topic/{project_name}-*")],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kafka-cluster:AlterGroup",
                        "kafka-cluster:DescribeGroup",
                    ],
                    "Resource": [
                        get_arn_template("kafka", f"group/{project_name}-*"),
                        get_arn_template("kafka", f"group/{project_name}-*"),
                    ],
                },
            ],
        }
    ),
)
msk_connector_service_role = aws.iam.Role(
    f"{project_name}-msk-service-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "kafkaconnect.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
    managed_policy_arns=[msk_policy.arn],
)


pulumi.export("task_execution_role_arn", task_execution_role.arn)
pulumi.export("api_task_role_arn", api_task_role.arn)
pulumi.export("data_generator_task_role_arn", data_generator_role.arn)
pulumi.export("data_processor_task_role_arn", api_task_role.arn)
pulumi.export("kafka_bridge_task_role_arn", api_task_role.arn)
