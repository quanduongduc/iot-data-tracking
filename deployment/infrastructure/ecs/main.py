import sys

sys.path.append("../../")

import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix

from infrastructure.ecs.shared_ecs import cluster
from infrastructure.ecs.api import api_on_demand_service
from infrastructure.ecs.data_gererator import dg_on_demand_service
from infrastructure.ecs.mosquitto import mqtt_on_demand_service
from infrastructure.ecs.kafka_mqtt_bridge import bridge_on_demand_service
from infrastructure.ecs.data_processor import dp_on_demand_service