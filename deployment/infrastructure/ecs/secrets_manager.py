import json
import pulumi
import pulumi_aws as aws
from infrastructure.environment import prefix, stack_name
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import pulumi_random as random

ENVIRONMENT = stack_name.upper()
DB_PASSWORD = random.RandomPassword(f"{prefix}-db-password", length=30, special=True)
DB_PORT = 5432
DB_USER = "fastapi_user"
DB_NAME = "fastapi_ecs"

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

secrets_dict = {
    "ENVIRONMENT": ENVIRONMENT,
    "POSTGRES_HOST": "localhost",  # "localhost" is a placeholder, the actual value will be replaced by the DATABASE CLUSTER ENDPOINT
    "POSTGRES_PORT": DB_PORT,
    "POSTGRES_USER": DB_USER,
    "POSTGRES_DB": DB_NAME,
    "JWT_ALG":JWT_ALG,
    "JWT_PRIVATE_KEY": JWT_PRIVATE_PEM.decode("utf-8"),
    "JWT_PUBLIC_KEY": JWT_PUBLIC_PEM.decode("utf-8"),
    "JWT_ACCESS_EXP": JWT_ACCESS_EXP,
    "JWT_REFRESH_EXP": JWT_REFRESH_EXP,
    "CORS_HEADERS": CORS_HEADERS,
    "CORS_ORIGINS": CORS_ORIGINS,
}

secret = aws.secretsmanager.Secret(f"{prefix}-secret")
secret_version = aws.secretsmanager.SecretVersion(
    f"{prefix}-secret-version",
    secret_id=secret.id,
    secret_string=DB_PASSWORD.result.apply(
        lambda pwd: json.dumps({**secrets_dict, "POSTGRES_PASSWORD": pwd})
    ),
)

pulumi.export("secret_name", secret.name)
