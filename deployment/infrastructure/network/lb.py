import json
import pulumi
import pulumi_aws as aws
from infrastructure.environment import project_name
from infrastructure.network.vpc import (
    ecs_private_subnet1,
    ecs_private_subnet2,
    alb_sg,
    mqtt_lb_sg,
)


log_bucket = aws.s3.Bucket(
    f"{project_name}-alb-log-bucket",
    acl="private",
    force_destroy=True,
)

caller_identity = aws.get_caller_identity()
bucket_policy = aws.s3.BucketPolicy(
    f"{project_name}-alb-log-bucket-policy",
    bucket=log_bucket.id,
    policy=pulumi.Output.all(log_bucket.arn, caller_identity.arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Principal": {
                            "AWS": [
                                args[1],
                            ]
                        },
                        "Effect": "Allow",
                        "Action": "s3:GetBucketAcl",
                        "Resource": args[0],
                    },
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "delivery.logs.amazonaws.com"},
                        "Action": "s3:PutObject",
                        "Resource": f"{args[0]}/*",
                    },
                ],
            }
        )
    ),
)

alb = aws.lb.LoadBalancer(
    f"{project_name}-alb",
    internal=True,
    subnets=[ecs_private_subnet1, ecs_private_subnet2],
    security_groups=[alb_sg.id],
    load_balancer_type="application",
)


alb_listener = aws.lb.Listener(
    f"{project_name}-alb-listener",
    load_balancer_arn=alb.arn,
    port=80,
    protocol="HTTP",
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="fixed-response",
            fixed_response=aws.lb.ListenerDefaultActionFixedResponseArgs(
                content_type="text/plain",
                message_body="Service is unavailable",
                status_code="503",
            ),
        )
    ],
)

pulumi.export("alb_listener_arn", alb_listener.arn)
