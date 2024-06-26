import json

from infrastructure.environment import prefix
import pulumi
import pulumi_aws as aws
from infrastructure.ecs.shared_ecs import role_stack

config = pulumi.Config()
source_data_path = config.require_object("source_data_path").get("value")
api_task_role_arn = role_stack.get_output("api_task_role_arn")
dg_task_role_arn = role_stack.get_output("data_generator_task_role_arn")

source_data_bucket = aws.s3.Bucket(
    f"{prefix}-source-data",
    opts=pulumi.ResourceOptions(retain_on_delete=True),
)

s3_msk_plugin_access_policy = aws.s3.BucketPublicAccessBlock(
    "my-bucket-public-access-block",
    bucket=source_data_bucket.id,
    block_public_acls=False,
    ignore_public_acls=False,
    block_public_policy=False,
    restrict_public_buckets=False,
    opts=pulumi.ResourceOptions(retain_on_delete=True),
)

source_data_bucket_ownership_controls = aws.s3.BucketOwnershipControls(
    f"{prefix}-source-data-ownership-controls",
    bucket=source_data_bucket.bucket,
    rule=aws.s3.BucketOwnershipControlsRuleArgs(
        object_ownership="BucketOwnerPreferred"
    ),
    opts=pulumi.ResourceOptions(retain_on_delete=True),
)

caller_identity = aws.get_caller_identity()


def create_policy(args):
    caller_arn, bucket_id, api_task_role_arn, dg_task_role_arn = args
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InternalReadPolicy",
                "Effect": "Allow",
                "Principal": {
                    "AWS": [
                        caller_arn,
                        api_task_role_arn,
                        dg_task_role_arn,
                    ]
                },
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:GetObject",
                    "s3:GetObjectAcl",
                    "s3:DeleteObject",
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_id}/*",
                    f"arn:aws:s3:::{bucket_id}/*",
                ],
            }
        ],
    }
    return json.dumps(policy)


policy_output = pulumi.Output.all(
    caller_identity.arn,
    source_data_bucket.id,
    api_task_role_arn,
    dg_task_role_arn
).apply(create_policy)

s3_bucket_policy_attachment = aws.s3.BucketPolicy(
    f"{prefix}-bucket-policy-attachment",
    bucket=source_data_bucket.id,
    policy=policy_output,
    opts=pulumi.ResourceOptions(retain_on_delete=True),
)


s3_lambda_function = aws.s3.Bucket(
    f"{prefix}-lambda-function-bucket",
    
)