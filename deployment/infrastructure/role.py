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
