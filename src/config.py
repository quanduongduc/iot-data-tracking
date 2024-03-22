import os
from typing import List
from pydantic import AnyUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings

from src.constanst import Environment

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = AppSettings()
