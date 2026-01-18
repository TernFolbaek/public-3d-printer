from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API configuration
    api_url: str = "http://localhost:8000"
    api_key: str = ""

    # Bambu P1S configuration
    bambu_ip: str = ""
    bambu_serial: str = ""
    bambu_access_code: str = ""

    # Polling configuration
    poll_interval_seconds: int = 30
    progress_update_interval_seconds: int = 10

    # File storage
    download_dir: str = "/tmp/print-jobs"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
