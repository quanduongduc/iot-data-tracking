import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
from environment import get_arn_template, project_name

ecr_read_policy = aws.iam.Policy(
    f"{project_name}-ecr-read-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "ecr:BatchCheckLayerAvailability",
                    ],
                    "Resource": get_arn_template(
                        service="ecr", resource_name=f"{project_name}-*"
                    ),
                }
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
                        service="logs", resource_name=f"{project_name}-*"
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
    managed_policy_arns=[cloudwatch_policy.arn, ecr_read_policy.arn],
)


s3_read_policy = aws.iam.Policy(
    f"{project_name}-s3-read-policy",
    description="A policy to allow read access to S3",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:GetObject", "s3:ListBucket"],
                    "Resource": [
                        get_arn_template(
                            service="s3", resource_name=f"{project_name}-*"
                        ),
                    ],
                    "Effect": "Allow",
                }
            ],
        }
    ),
)

ec2_api_role = aws.iam.Role(
    f"{project_name}-ec2-api-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    },  # replace with the service you want
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
    managed_policy_arns=[s3_read_policy.arn],
)
