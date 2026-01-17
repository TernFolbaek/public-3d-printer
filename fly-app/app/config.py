from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/printqueue"

    # JWT
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # OAuth - GitHub
    github_client_id: str = ""
    github_client_secret: str = ""

    # Tigris S3-compatible storage
    tigris_access_key_id: str = ""
    tigris_secret_access_key: str = ""
    tigris_endpoint_url: str = "https://fly.storage.tigris.dev"
    tigris_bucket_name: str = "print-jobs"
    tigris_region: str = "auto"

    # App settings
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # File upload limits
    max_file_size_mb: int = 100

    # Printer API
    printer_api_key: str = "46de2e04fb4409dd59acb054fb43d728c457d3b37fec2cfcd5ff1751df58aeeb"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
