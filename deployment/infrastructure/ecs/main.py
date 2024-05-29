import sys

sys.path.append("../../")

import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix

from infrastructure.ecs.shared_ecs import cluster
from infrastructure.ecs.spot_shutdown import spot_shutdown_lambda