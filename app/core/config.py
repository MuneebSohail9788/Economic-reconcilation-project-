from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:///./economic_truth_engine.db"
    storage_dir: str = "./storage"
    max_upload_mb: int = 25
    extraction_mode: str = "ai"
    fixture_path: str = "./tests/fixtures/extraction_fixtures.json"
    max_retries: int = 3
    ai_provider_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_timeout_seconds: float = 60.0
    api_auth_enabled: bool = False
    api_key: str | None = None
    request_timeout_seconds: float = 60.0
    allowed_origins: str = "http://localhost:8000"
    trusted_hosts: str = "localhost,127.0.0.1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
