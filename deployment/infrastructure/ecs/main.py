import sys

sys.path.append("../../")

import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix

from infrastructure.ecs.shared_ecs import cluster
from infrastructure.ecs.api import api_capacity_provider
from infrastructure.ecs.data_gererator import data_generator_capacity_provider
from infrastructure.ecs.mosquitto import mqtt_capacity_provider
from infrastructure.ecs.kafka_mqtt_bridge import kafka_bridge_capacity_provider
from infrastructure.ecs.data_processor import data_processor_capacity_provider

cluster_capacity_providers = aws.ecs.ClusterCapacityProviders(
    f"{prefix}-cluster-capacity-providers",
    cluster_name=cluster.name,
    capacity_providers=[
        api_capacity_provider.name,
        data_generator_capacity_provider.name,
        mqtt_capacity_provider.name,
        kafka_bridge_capacity_provider.name,
        data_processor_capacity_provider.name,
    ],
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)
