import pulumi
import pulumi_aws as aws

project_name = pulumi.get_project()
stack_name = pulumi.get_stack()
prefix = f"{project_name}-{stack_name}"
account_id = aws.get_caller_identity().account_id
region = aws.get_region().name


def get_arn_template(service: str, resource_name: str):
    return f"arn:aws:{service}:{region}:{account_id}:{resource_name}"
