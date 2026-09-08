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
    OLLAMA_MODEL: str = "qwen3"
    OCR_MODEL: str = "deepseek-ocr"
    OCR_PAGE_DPI: int = 200
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