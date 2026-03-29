from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from datetime import date


class Settings(BaseSettings):
    """Loads `GEMINI_API_KEY` and other vars from the environment and `serene-backend/.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = Field(default="dummy_key", description="Google AI Studio API key for Gemini")
    openai_api_key: str = Field(default="dummy_key", description="OpenAI key for Whisper voice transcription")
    database_url: str = "sqlite:///./serene.db"
    process_start_date: str = "2024-01-01"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("gemini_api_key", "openai_api_key", mode="before")
    @classmethod
    def strip_secret_strings(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        s = v.strip()
        if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
            s = s[1:-1].strip()
        return s

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def process_start(self) -> date:
        return date.fromisoformat(self.process_start_date)

    @property
    def gemini_configured(self) -> bool:
        k = self.gemini_api_key
        return bool(k and k != "dummy_key")


@lru_cache
def get_settings() -> Settings:
    return Settings()
