"""All settings come from environment variables. Secrets (GROQ_API_KEY) live only
on the server and are never sent to the browser or committed to Git."""
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class Settings:
    ENV = os.getenv("ENV", "development")            # "production" disables /docs
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    # Comma-separated list of frontend URLs allowed to call this API (CORS)
    ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_data")

    MAX_FILE_MB = _int("MAX_FILE_MB", 10)
    MAX_FILES_PER_UPLOAD = _int("MAX_FILES_PER_UPLOAD", 5)
    MAX_PAGES_PER_FILE = _int("MAX_PAGES_PER_FILE", 200)
    CHUNK_SIZE = _int("CHUNK_SIZE", 800)             # characters per chunk
    CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 150)       # characters shared between chunks
    TOP_K = _int("TOP_K", 4)                         # chunks sent to the LLM
    MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.85"))  # cosine distance cutoff
    RATE_LIMIT_PER_MIN = _int("RATE_LIMIT_PER_MIN", 30)


settings = Settings()
