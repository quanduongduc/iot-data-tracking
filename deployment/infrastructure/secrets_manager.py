import json
import pulumi_aws as aws
from environment import prefix, stack_name
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import pulumi_random as random

db_password = random.RandomPassword(f"{prefix}-db-password", length=30, special=True)
db_port = 5432
db_username = "fastapi_user"
db_name = "fastapi_ecs"

jwt_private_key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
jwt_public_key = jwt_private_key.public_key()

jwt_private_pem = jwt_private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
)
jwt_public_pem = jwt_public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

JWT_ACCESS_EXP = 3600
JWT_REFRESH_EXP = 3600 * 24 * 7

CORS_HEADERS = "*"
CORS_ORIGINS = "*"

secrets_dict = {
    "POSTGRES_HOST": "localhost",  # "localhost" is a placeholder, the actual value will be replaced by the DATABASE CLUSTER ENDPOINT
    "POSTGRES_PORT": db_port,
    "POSTGRES_USERNAME": db_username,
    "POSTGRES_DB": db_name,
    "JWT_PRIVATE_KEY": jwt_private_pem.decode("utf-8"),
    "JWT_PUBLIC_KEY": jwt_public_pem.decode("utf-8"),
    "JWT_ACCESS_EXP": JWT_ACCESS_EXP,
    "JWT_REFRESH_EXP": JWT_REFRESH_EXP,
    "CORS_HEADERS": CORS_HEADERS,
    "CORS_ORIGINS": CORS_ORIGINS,
}

secret = aws.secretsmanager.Secret(f"{prefix}-secret")
secret_version = aws.secretsmanager.SecretVersion(
    f"{prefix}-secret-version",
    secret_id=secret.id,
    secret_string=db_password.result.apply(
        lambda pwd: json.dumps({**secrets_dict, "POSTGRES_PASSWORD": pwd})
    ),
)
