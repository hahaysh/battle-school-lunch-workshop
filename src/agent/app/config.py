from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_host: str = "0.0.0.0"
    agent_port: int = 8090
    mcp_url: str = "http://localhost:8080/mcp"
    cors_origins: str = "http://localhost:3000"
    # Foundry is intentionally optional: deterministic scoring remains available
    # for local development and tests without credentials.
    foundry_project_endpoint: str = ""
    foundry_api_key: str = ""
    foundry_model: str = "gpt-4o-mini"
    database_path: str = "./data/analyses.db"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
