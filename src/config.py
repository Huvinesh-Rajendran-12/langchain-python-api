import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Database settings
    DB_USERNAME: str = os.getenv("DB_USERNAME", "default_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "default_password")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "default_db")

    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # LLM settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_LLM_MODEL: str = os.getenv("ANTHROPIC_LLM_MODEL", "claude-3-5-sonnet-20240620")
    ANTHROPIC_LLM_TEMPERATURE: float = float(os.getenv("ANTHROPIC_LLM_TEMPERATURE", "0"))
    ANTHROPIC_LLM_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_LLM_MAX_TOKENS", "1000"))

    # Caching settings
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "True").lower() == "true"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Create a global instance of the settings
settings = Settings()
