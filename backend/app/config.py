import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    postgres_user: str = "ethanalyst"
    postgres_password: str = "ethanalyst_secret"
    postgres_db: str = "eth_behavior"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # Ethereum Node
    eth_rpc_http: str = "http://100.100.0.126:8547"
    eth_rpc_ws: str = "ws://100.100.0.126:8548"
    eth_beacon_api: str = "http://100.100.0.126:5052"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 3001

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    class Config:
        env_file = ".env"


settings = Settings()
