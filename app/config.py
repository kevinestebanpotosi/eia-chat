import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Qdrant ---
    QDRANT_URL: str | None = os.getenv("QDRANT_URL")
    QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "COMPLETA")

    # --- Azure OpenAI (embeddings) ---
    AZURE_OPENAI_API_KEY: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "text-embedding-3-small")

    # --- Groq ---
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GROQ_ROUTER_MODEL: str = os.getenv("GROQ_ROUTER_MODEL", "llama-3.1-8b-instant")
    GROQ_CHAT_MODEL: str = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")

    # --- Redis/Valkey (memory) ---
    REDIS_URL: str | None = os.getenv("REDIS_URL") or os.getenv("VALKEY_URL")

    # --- Gateway ---
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()


def validate_settings() -> None:
    required = [
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "GROQ_API_KEY",
    ]
    missing = [name for name in required if not getattr(settings, name, None)]
    if missing:
        raise ValueError(f"Faltan variables en .env: {', '.join(missing)}")
