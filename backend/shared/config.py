from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "root"

    # Настройки LLM: "gemini", "ollama" или "mock"
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    
    # Настройки Ollama (локальная модель)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder"  # или llama3, codellama

    @property
    def DB_ASYNC_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=(
            ROOT_DIR / ".env",
            BASE_DIR / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()