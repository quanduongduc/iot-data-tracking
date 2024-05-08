import json
import pulumi
import pulumi_aws as aws
from infrastructure.ecs.shared_ecs import role_stack, network_stack
from infrastructure.environment import prefix
from infrastructure.ecs.s3 import mqtt_source_plugin_name, s3_msk_plugin

ecs_private_subnet1_id = network_stack.get_output("ecs_private_subnet1_id")
ecs_private_subnet2_id = network_stack.get_output("ecs_private_subnet2_id")
kafka_connect_role_name = role_stack.get_output("kafka_connect_role_name")
kafka_client_sg_id = network_stack.get_output("kafka_client_sg_id")
msk_connector_service_role_arn = role_stack.get_output("msk_connector_service_role_arn")

msk_cluster = aws.msk.Cluster(
    f"{prefix}-msk-cluster",
    cluster_name=f"{prefix}-msk-cluster",
    kafka_version="2.6.1",
    number_of_broker_nodes=2,
    broker_node_group_info=aws.msk.ClusterBrokerNodeGroupInfoArgs(
        instance_type="kafka.m5.large",
        ebs_volume_size=50,
        client_subnets=[ecs_private_subnet1_id, ecs_private_subnet2_id],
        security_groups=[kafka_client_sg_id],
    ),
    number_of_broker_nodes=2,
)

mqtt_sink_plugin = aws.mskconnect.CustomPlugin(
    f"{prefix}-msk-connect-mqtt-sink",
    content_type="ZIP",
    location=aws.mskconnect.CustomPluginLocationArgs(
        s3=aws.mskconnect.CustomPluginLocationS3Args(
            bucket_arn=s3_msk_plugin.arn,
            file_key=f"{mqtt_source_plugin_name}",
        ),
    ),
)

def get_connector_configuration(args):
    return {}


connector = aws.mskconnect.Connector(
    f"{prefix}-msk-connector",
    capacity=aws.mskconnect.ConnectorCapacityArgs(
        autoscaling=aws.mskconnect.ConnectorCapacityAutoscalingArgs(
            mcu_count=1,
            max_worker_count=2,
            min_worker_count=1,
        ),
    ),
    connector_configuration={"bootstrap.servers": msk_cluster.bootstrap_brokers},
    kafka_cluster=aws.mskconnect.ConnectorKafkaClusterArgs(
        apache_kafka_cluster=aws.mskconnect.ConnectorKafkaClusterApacheKafkaClusterArgs(
            bootstrap_servers=msk_cluster.bootstrap_brokers,
            vpc=aws.mskconnect.ConnectorKafkaClusterApacheKafkaClusterVpcArgs(
                subnets=[ecs_private_subnet1_id, ecs_private_subnet2_id],
                security_groups=[kafka_client_sg_id],
            ),
        )
    ),
    kafkaconnect_version="2.7.0",
    plugins=[mqtt_sink_plugin.arn],
    service_execution_role_arn=msk_connector_service_role_arn,
)
