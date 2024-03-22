from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    PRODUCTION = "PRODUCTION"
    LOCAL = "LOCAL"
    @property
    def alias(self) -> str:
        return {self.DEVELOPMENT: "dev", self.PRODUCTION: "prod",self.LOCAL: "local"}.get(self, "unknown")

    @property
    def is_development(self) -> bool:
        return self in (self.DEVELOPMENT)

    @property
    def is_production(self) -> bool:
        return self in (self.PRODUCTION)


SHOW_DOCS_ENVIRONMENT = {Environment.DEVELOPMENT}
