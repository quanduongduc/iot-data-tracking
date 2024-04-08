import json
import pulumi
import pulumi_aws as aws
from infrastructure.environment import project_name
from infrastructure.network.vpc import vpc

domain_name = pulumi.Config().require("domain_name")
zone = aws.route53.Zone(
    f"{project_name}-hosted-zone",
    name=domain_name,
    opts=pulumi.ResourceOptions(
        delete_before_replace=True, replace_on_changes=["vpcs"]
    ),
)


pulumi.export("hosted_zone_id", zone.zone_id)
