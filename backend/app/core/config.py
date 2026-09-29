import uuid

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # "production" in the Docker image (Dockerfile sets APP_ENV); see validate_runtime.
    app_env: str = "dev"
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


def validate_runtime(s: Settings) -> None:
    """Refuse to start a production instance with development-only auth bypasses."""
    if s.app_env != "production":
        return
    if s.auth_stub:
        raise RuntimeError(
            "AUTH_STUB=true is not allowed when APP_ENV=production: "
            "every request would be authenticated as a stub user."
        )
    if s.mcp_agent_user_id is not None and not s.mcp_agents:
        raise RuntimeError(
            "MCP_AGENT_USER_ID without MCP_AGENTS is not allowed when APP_ENV=production: "
            "the MCP endpoint would accept calls without a key. Use service account keys (ADR-017)."
        )


settings = Settings()
