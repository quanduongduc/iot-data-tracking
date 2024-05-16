import pulumi
import pulumi_aws as aws
from infrastructure.ecs.shared_ecs import role_stack, network_stack
from infrastructure.environment import prefix

ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
kafka_connect_role_name = role_stack.get_output("kafka_connect_role_name")
msk_sg_id = network_stack.get_output("msk_sg_id")


msk_configuration = aws.msk.Configuration(
    f"{prefix}-msk-configuration",
    kafka_versions=["2.6.1"],
    server_properties="""
    auto.create.topics.enable = true
    delete.topic.enable = true
    num.partitions = 5
    """,
)


msk_cluster = aws.msk.Cluster(
    f"{prefix}-msk-cluster",
    cluster_name=f"{prefix}-msk-cluster",
    kafka_version="2.6.1",
    number_of_broker_nodes=2,
    encryption_info=aws.msk.ClusterEncryptionInfoArgs(
        encryption_in_transit=aws.msk.ClusterEncryptionInfoEncryptionInTransitArgs(
            client_broker="PLAINTEXT", in_cluster=True
        )
    ),
    client_authentication=aws.msk.ClusterClientAuthenticationArgs(
        unauthenticated=True,
    ),
    broker_node_group_info=aws.msk.ClusterBrokerNodeGroupInfoArgs(
        instance_type="kafka.t3.small",
        client_subnets=[ecs_private_subnet1_id, ecs_private_subnet2_id],
        security_groups=[msk_sg_id],
        storage_info=aws.msk.ClusterBrokerNodeGroupInfoStorageInfoArgs(
            ebs_storage_info=aws.msk.ClusterBrokerNodeGroupInfoStorageInfoEbsStorageInfoArgs(
                volume_size=50,
            ),
        ),
    ),
    configuration_info=aws.msk.ClusterConfigurationInfoArgs(
        arn=msk_configuration.arn,
        revision=msk_configuration.latest_revision,
    ),
    opts=pulumi.ResourceOptions(ignore_changes=["encryption_info"]),
)


KAFKA_WEATHER_DATA_TOPIC = "weather.data"
KAFKA_WEATHER_DATA_GROUP_ID = "weather-data-processing"
