from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://intel:intel@localhost:5432/intel"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "any"
    s3_secret_key: str = "any"
    s3_bucket: str = "raw-evidence"

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-oss:20b"
    llm_timeout_sec: int = 300
    embed_model: str = "nomic-embed-text"
    embed_dim: int = 768
    llm_enabled: bool = True

    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_from: str = ""
    alert_email_to: str = ""
    alert_threshold: float = 0.75

    github_token: str = ""
    nvd_api_key: str = ""
    # Never backfill items older than this on first sight — whole historic
    # catalogues (KEV 2014, blog archives) would swamp the store otherwise.
    backfill_max_age_days: int = 30
    # Required for any mutating API call; empty means writes fail closed.
    api_write_key: str = ""

    processing_version: str = "0.2.0"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
