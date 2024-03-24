import pulumi

project_name = pulumi.get_project()
stack_name = pulumi.get_stack()
prefix = f"{project_name}-{stack_name}"
