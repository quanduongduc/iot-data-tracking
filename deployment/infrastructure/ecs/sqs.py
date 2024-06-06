import json
import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix
from infrastructure.ecs.shared_ecs import cluster

sqs_shutdown_queue = aws.sqs.Queue(
    f"{prefix}-sqs-shutdown-queue",
    visibility_timeout_seconds=30
)

event_shutdown_rule = aws.cloudwatch.EventRule(
    f"{prefix}-event-shutdown-rule",
    event_bus_name="default",
    event_pattern=pulumi.Output.all(cluster.arn).apply(
        lambda arn: json.dumps({
            "source": [
                "aws.ecs"
            ],
            "detail-type": [
                "ECS Task State Change"
            ],
            "detail": {
                "stopCode": ["SpotInterruption"],
                "clusterArn": arn
            }
        })
    )
)


event_shutdown_target = aws.cloudwatch.EventTarget(
    f"{prefix}-event-shutdown-target",
    rule=event_shutdown_rule.name,
    arn=sqs_shutdown_queue.arn,
)

sqs_shutdown_queue_policy = aws.sqs.QueuePolicy(
    f"{prefix}-sqs-shutdown-queue-policy",
    queue_url=sqs_shutdown_queue.url,
    policy=pulumi.Output.all(sqs_shutdown_queue.arn, event_shutdown_rule.arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "events.amazonaws.com"},
                        "Action": "sqs:SendMessage",
                        "Resource": args[0],
                        "Condition": {
                            "ArnEquals": {"aws:SourceArn": args[1]}
                        },
                    }
                ],
            }
        )
    ),
)
