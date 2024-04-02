import json
import logging
import os
from typing import Any, List, Tuple, Type, cast
from boto3 import Session
from pydantic.fields import FieldInfo
from pydantic import AnyUrl, PostgresDsn, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    EnvSettingsSource,
)

from src.constanst import Environment


session = Session()
secretsmanager_client = session.client(service_name="secretsmanager")


class SecretManagerSource(EnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> str | dict[str, Any]:
        secret_string = secretsmanager_client.get_secret_value(SecretId=field_name)[
            "SecretString"
        ]
        try:
            return json.loads(secret_string)
        except json.decoder.JSONDecodeError:
            return secret_string
        except Exception as e:
            logging.error(f"Error while fetching secret {field_name}: {e}")


class AppSettings(BaseSettings):
    ENVIRONMENT: Environment

    JWT_ALG: str
    JWT_EXP: int
    JWT_SECRET: SecretStr
    SECURE_COOKIES: bool

    CORS_HEADERS: List[str]
    CORS_ORIGINS: List[AnyUrl]

    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    @property
    def postgres_dsn(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql",
            user=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=f"/{self.POSTGRES_DB}",
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.is_production

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.is_development

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (SecretManagerSource(settings_cls),)


settings = AppSettings()
