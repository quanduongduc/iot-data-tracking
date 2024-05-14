import json
import os

import pulumi_synced_folder
from infrastructure.environment import prefix
import pulumi
import pulumi_aws as aws
from infrastructure.ecs.shared_ecs import role_stack

config = pulumi.Config()
source_data_path = config.require_object("source_data_path").get("value")
ec2_role_name = role_stack.get_output("ec2_api_role_name")
dg_role_name = role_stack.get_output("ec2_data_generator_role_name")

source_data_bucket = aws.s3.Bucket(
    f"{prefix}-source-data",
)

s3_msk_plugin_access_policy = aws.s3.BucketPublicAccessBlock(
    "my-bucket-public-access-block",
    bucket=source_data_bucket.id,
    block_public_acls=False,
    ignore_public_acls=False,
    block_public_policy=False,
    restrict_public_buckets=False,
)

source_data_bucket_ownership_controls = aws.s3.BucketOwnershipControls(
    f"{prefix}-source-data-ownership-controls",
    bucket=source_data_bucket.bucket,
    rule=aws.s3.BucketOwnershipControlsRuleArgs(
        object_ownership="BucketOwnerPreferred"
    ),
)

caller_identity = aws.get_caller_identity()


def create_policy(args):
    caller_arn, bucket_id, account_id, ec2_role_name, dg_role_name = args
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InternalReadPolicy",
                "Effect": "Allow",
                "Principal": {
                    "AWS": [
                        caller_arn,
                        f"arn:aws:iam::{account_id}:role/{ec2_role_name}",
                        f"arn:aws:iam::{account_id}:role/{dg_role_name}",
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
    caller_identity.account_id,
    ec2_role_name,
    dg_role_name,
).apply(create_policy)

s3_bucket_policy_attachment = aws.s3.BucketPolicy(
    f"{prefix}-bucket-policy-attachment",
    bucket=source_data_bucket.id,
    policy=policy_output,
)
