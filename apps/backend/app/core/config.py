from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str = "hr-os-dev-secret-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    UPLOAD_DIR: str = "storage/uploads"
    OLLAMA_URL: str = "http://localhost:11434"
    # Primary general model for non-critical AI work (HR email assistant,
    # job assistant, structured profile parsing) = Qwen3-8B Q4.
    OLLAMA_MODEL: str = "qwen3:latest"
    # Faster/smaller model for CV profile parsing. Falls back to OLLAMA_MODEL
    # when empty (e.g. "qwen2.5:3b" — already small and quick).
    OLLAMA_PROFILE_MODEL: str = ""
    # Vision OCR model for scanned / image-only PDF CVs (run: ollama pull deepseek-ocr).
    # Only invoked when a PDF has no native text layer.
    OLLAMA_OCR_MODEL: str = "deepseek-ocr"
    # Scanned-CV OCR limits: first N pages rendered at DPI (speed vs accuracy).
    OCR_MAX_PAGES: int = 5
    OCR_DPI: int = 150
    # Warm-up the OCR model in the background on startup so the first scanned
    # CV is not stuck behind a multi-GB cold load.
    OCR_WARMUP_ON_STARTUP: bool = True
    # How long Ollama keeps the model loaded in memory. "10m" avoids cold-start
    # latency on repeat calls. "-1" keeps it loaded forever (uses more RAM),
    # "0" unloads immediately.
    OLLAMA_KEEP_ALIVE: str = "10m"
    # Max number of CV parse results to keep in memory (same file re-upload =
    # instant, no model call).
    PROFILE_CACHE_SIZE: int = 128
    # Primary candidate evaluation / AI screening model = Qwen3-8B Q4.
    OLLAMA_EVALUATION_MODEL: str = "qwen3:latest"
    # Second pass for ambiguous (UNCLEAR) screenings. Empty = disabled (fastest,
    # the 8B primary result is kept). To keep a second opinion set it to another
    # model that is actually pulled, e.g. "qwen3:latest".
    OLLAMA_FALLBACK_EVALUATION_MODEL: str = ""
    # Tiny model dedicated to email drafting = Qwen3-1.7B. Run:
    # ollama pull qwen3:1.7b
    EMAIL_MODEL: str = "qwen3:1.7b"
    # Sender identity used in drafted emails (sign-off / body mentions).
    COMPANY_NAME: str = ""
    HR_NAME: str = ""
    # Company office address, included for onsite interview emails.
    COMPANY_LOCATION: str = ""
    # Public base URL used to build candidate-facing links (job invites).
    PUBLIC_BASE_URL: str = "http://localhost:3001"
    # Email reply agent: replies with an interview follow-up when a candidate
    # answers an email, re-invites after a missed interview, and cancels the
    # remaining interviews once a candidate is selected.
    REPLY_AGENT_ENABLED: bool = True
    REPLY_AGENT_INTERVAL_SECONDS: int = 60
    MISSED_INTERVIEW_GRACE_MINUTES: int = 15
    # Auto-send talent-pool invite emails when a job is published (matched by
    # job title) and how many days an invite link stays valid.
    TALENT_POOL_INVITES_ON_PUBLISH: bool = True
    TALENT_POOL_INVITE_DAYS: int = 14
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
    # Inbound mailbox (IMAP) support for the reply agent. When IMAP_ENABLED and
    # EMAIL_ENABLED are true, the reply-agent loop and the "Check inbox" button
    # fetch unseen messages, record the candidate's message in the dashboard
    # chat, and answer queries automatically. For Gmail use IMAP_HOST
    # imap.gmail.com, port 993, with the same app password as SMTP_USER.
    IMAP_ENABLED: bool = False
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_FOLDER: str = "INBOX"
    AUTO_EVALUATE_ON_APPLY: bool = True
    AUTO_REJECT_THRESHOLD: int = 40
    AUTO_REJECT_FLOOR: int = 20
    # Hard deadline for the LangGraph screening run in the auto path. A full
    # run is 7 sequential LLM nodes (plus a possible 14B second-pass), and on
    # CPU inference that can legitimately take several minutes, so the cap is
    # generous. When a run exceeds this, evaluation falls back to the bounded
    # legacy screening so every CV gets a result even if Ollama is cold/slow.
    # 0 disables the cap.
    AUTO_SCREEN_TIMEOUT_SECONDS: int = 360
    TOP_CANDIDATE_COUNT: int = 10
    # --- Langfuse observability / evaluation -------------------------------
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "http://localhost:3000"
    # Judge model for LLM-as-a-judge evaluation runs. Empty = use OLLAMA_MODEL.
    EVAL_JUDGE_MODEL: str = ""
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