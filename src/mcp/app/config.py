from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    neis_api_key: str = Field(default="", repr=False)
    neis_base_url: str = "https://open.neis.go.kr/hub"
    neis_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    neis_max_retries: int = Field(default=2, ge=0, le=5)
    mcp_host: str = "0.0.0.0"
    mcp_port: int = Field(default=8080, gt=0, le=65535)


@lru_cache
def get_settings() -> Settings:
    return Settings()
