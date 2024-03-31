**Prerequisite**

Before proceeding, ensure you meet the following requirements:

1. Add your AWS credentials to the AWS configuration.
1. Install Pulumi. You can find installation instructions [here](https://www.pulumi.com/docs/get-started/install/).
3. Install the dependencies listed in `requirements/local.txt`.

**Usage**

Once you've fulfilled these prerequisites, you can proceed with deploying the infrastructure using Pulumi.
To deploy the infrastructure, you need to have Pulumi installed and configured with your AWS credentials. Then, you can run the following command in the infrastructure directory:

This command will preview the changes to be made and, after confirmation, apply the changes. You can see the status of your stack at any time with the `pulumi stack` command.

```
cmd pulumi up
```

**Topology**

![ecs-fastapi (1)](https://github.com/quanduongduc/fastapi-ecs/assets/59951771/db7df046-0309-4a23-9c56-f4f5eb9a7aac)
