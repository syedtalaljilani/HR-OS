from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent.parent / "app" / "db" / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str = "hr-os-dev-secret-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    UPLOAD_DIR: str = "storage/uploads"
    OLLAMA_URL: str = "http://localhost:11434"
    # Primary general model for non-critical AI work (HR email assistant,
    # job assistant, structured profile parsing) = Qwen3-8B Q4.
    OLLAMA_MODEL: str = "qwen3"
    # Faster/smaller model for CV profile parsing. Falls back to OLLAMA_MODEL
    # when empty (e.g. "qwen2.5:3b" — already small and quick).
    OLLAMA_PROFILE_MODEL: str = ""
    # How long Ollama keeps the model loaded in memory. "10m" avoids cold-start
    # latency on repeat calls. "-1" keeps it loaded forever (uses more RAM),
    # "0" unloads immediately.
    OLLAMA_KEEP_ALIVE: str = "10m"
    # Max number of CV parse results to keep in memory (same file re-upload =
    # instant, no model call).
    PROFILE_CACHE_SIZE: int = 128
    # Primary candidate evaluation / AI screening model = Qwen3-8B Q4.
    OLLAMA_EVALUATION_MODEL: str = "qwen3"
    # Larger model used to re-screen ambiguous cases = Qwen3-14B Q4 (e.g.
    # "qwen3:14b"). Only triggered when the primary 8B result is uncertain.
    OLLAMA_FALLBACK_EVALUATION_MODEL: str = "qwen3:14b"
    # Tiny model dedicated to email drafting = Qwen3-1.7B. Run:
    # ollama pull qwen3:1.7b
    EMAIL_MODEL: str = "qwen3:1.7b"
    # Sender identity used in drafted emails (sign-off / body mentions).
    COMPANY_NAME: str = ""
    HR_NAME: str = ""
    EMBEDDING_MODEL: str = "all-minilm"
    TRACKING_TOKEN_EXPIRE_DAYS: int = 90
    MAX_CV_SIZE_MB: int = 10
    EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "HR OS"
    AUTO_EVALUATE_ON_APPLY: bool = True
    AUTO_REJECT_THRESHOLD: int = 40
    AUTO_REJECT_FLOOR: int = 20
    TOP_CANDIDATE_COUNT: int = 10
    ALLOWED_CV_MIME: list[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]
    ALLOWED_CV_EXTENSIONS: list[str] = [".pdf", ".doc", ".docx", ".txt"]

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()