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

![image](https://github.com/quanduongduc/iot-data-tracking/assets/59951771/73440cc0-1029-4c86-ac4a-b89a978f9860)
