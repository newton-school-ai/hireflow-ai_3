"""
Application settings loaded from environment variables via pydantic-settings.
Usage:
    from src.config.settings import get_settings
    settings = get_settings()
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Central configuration for HireFlow.
    All values are loaded from the .env file or environment variables.
    """

    # --- LLM Provider ---
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")

    # Groq
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama3-8b-8192", alias="GROQ_MODEL")

    # Google Gemini
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")

    # --- Database ---
    database_url: str = Field(default="postgresql://localhost/hireflow", alias="DATABASE_URL")

    # --- Application ---
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    secret_key: str = Field(default="change_this_to_a_random_secret_string", alias="SECRET_KEY")
    allowed_origins: str = Field(default="http://localhost:3000", alias="ALLOWED_ORIGINS")

    # --- Storage ---
    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_path: str = Field(default="./data", alias="LOCAL_STORAGE_PATH")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()
