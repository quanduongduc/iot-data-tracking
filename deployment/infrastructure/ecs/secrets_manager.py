import json
import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix, stack_name
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

ENVIRONMENT = stack_name.upper()

JWT_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
JWT_PUBLIC_KEY = JWT_PRIVATE_KEY.public_key()

JWT_PRIVATE_PEM = JWT_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
)
JWT_PUBLIC_PEM = JWT_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


JWT_ALG = "RS256"
JWT_ACCESS_EXP = 3600
JWT_REFRESH_EXP = 3600 * 24 * 7

CORS_HEADERS = ["*"]
CORS_ORIGINS = ["*"]


secret = aws.secretsmanager.Secret(f"{prefix}-secret")

from infrastructure.ecs.mosquitto import (
    MQTT_PROCESSED_TOPIC,
    MQTT_SOURCE_TOPIC,
    mosquitto_nlb,
    mosquitto_nlb_mqtt_listener,
)
from infrastructure.ecs.s3 import source_data_bucket
from infrastructure.ecs.dynamodb import dynamodb_table
from infrastructure.ecs.rds import rds_instance
from infrastructure.ecs.msk import (
    KAFKA_WEATHER_DATA_GROUP_ID,
    KAFKA_WEATHER_DATA_TOPIC,
    msk_cluster,
)
from infrastructure.ecs.cache import elasticache_cluster

secrets_dict = {
    "ENVIRONMENT": ENVIRONMENT,
    "JWT_ALG": JWT_ALG,
    "JWT_PRIVATE_KEY": JWT_PRIVATE_PEM.decode("utf-8"),
    "JWT_PUBLIC_KEY": JWT_PUBLIC_PEM.decode("utf-8"),
    "JWT_ACCESS_EXP": JWT_ACCESS_EXP,
    "JWT_REFRESH_EXP": JWT_REFRESH_EXP,
    "CORS_HEADERS": CORS_HEADERS,
    "CORS_ORIGINS": CORS_ORIGINS,
    "MQTT_SOURCE_TOPIC": MQTT_SOURCE_TOPIC,
    "MQTT_PROCESSED_TOPIC": MQTT_PROCESSED_TOPIC,
    "KAFKA_WEATHER_DATA_TOPIC": KAFKA_WEATHER_DATA_TOPIC,
    "KAFKA_WEATHER_DATA_GROUP_ID": KAFKA_WEATHER_DATA_GROUP_ID,
    "REDIS_DB": "0",
}


secret_version = aws.secretsmanager.SecretVersion(
    f"{prefix}-secret-version",
    secret_id=secret.id,
    secret_string=pulumi.Output.all(
        mosquitto_nlb.dns_name,
        source_data_bucket.bucket,
        rds_instance.address,
        rds_instance.port,
        rds_instance.username,
        rds_instance.password,
        rds_instance.db_name,
        mosquitto_nlb_mqtt_listener.port,
        msk_cluster.bootstrap_brokers,
        elasticache_cluster.cache_nodes[0].address,
        elasticache_cluster.port,
        dynamodb_table.name,
    ).apply(
        lambda args: json.dumps(
            {
                **secrets_dict,
                "MQTT_BROKER_HOST": args[0],
                "S3_SOURCE_DATA_BUCKET": args[1],
                "MYSQL_HOST": args[2],
                "MYSQL_PORT": args[3],
                "MYSQL_USER": args[4],
                "MYSQL_PASSWORD": args[5],
                "MYSQL_DB": args[6],
                "MQTT_BROKER_PORT": args[7],
                "KAFKA_BOOTSTRAP_SERVERS": args[8],
                "REDIS_HOST": args[9],
                "REDIS_PORT": args[10],
                "DYNAMODB_TABLE_NAME": args[11],
            }
        ),
    ),
)