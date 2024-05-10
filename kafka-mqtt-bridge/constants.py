from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "DEV"
    PRODUCTION = "PROD"
    LOCAL = "LOCAL"

    @property
    def is_development(self) -> bool:
        return self in (self.DEVELOPMENT)

    @property
    def is_production(self) -> bool:
        return self in (self.PRODUCTION)
