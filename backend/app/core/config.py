import uuid

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://tasktrack:tasktrack@localhost:5432/tasktrack"
    auth_stub: bool = False
    keycloak_url: str = "https://auth.busypage.ru"
    keycloak_realm: str = "home"
    keycloak_client_id: str = "tasktrack"
    cors_origins: list[str] = ["http://localhost:5173"]

    # MCP server settings
    mcp_agent_user_id: uuid.UUID | None = None   # dev: single user, no key required
    mcp_agents: str = ""                          # prod: "key1:uuid1,key2:uuid2"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                import json
                return json.loads(stripped)
            return [o.strip() for o in stripped.split(",")]
        return v  # type: ignore[return-value]


settings = Settings()
