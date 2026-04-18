"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the AI Research Agent."""

    # LLM Provider
    LLM_PROVIDER: str = "groq"

    # API Keys
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""

    # Models
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_MODEL: str = "gpt-4o-mini"
    NVIDIA_MODEL: str = "meta/llama-3.1-70b-instruct"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Research
    MAX_SEARCH_RESULTS: int = 10
    MAX_SCRAPE_PAGES: int = 5
    REPORT_OUTPUT_DIR: str = "output"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
