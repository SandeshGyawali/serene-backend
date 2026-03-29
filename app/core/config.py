from pydantic_settings import BaseSettings
from functools import lru_cache
from datetime import date


class Settings(BaseSettings):
    gemini_api_key: str = "dummy_key"
    openai_api_key: str = "dummy_key"
    database_url: str = "sqlite:///./serene.db"
    process_start_date: str = "2024-01-01"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def process_start(self) -> date:
        return date.fromisoformat(self.process_start_date)

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
