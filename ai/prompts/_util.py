"""Builds a user prompt containing JSON-embedded metadata like prompt version."""
from datetime import datetime, timezone

PROMPT_VERSION_HEADER = (
    "PROMPT_VERSION={version}\n"
    "MODEL={model}\n"
    "Follow the exact JSON schema described in the system message.\n"
)


def with_metadata(prompt: str, *, version: str, model: str) -> str:
    return PROMPT_VERSION_HEADER.format(version=version, model=model) + prompt


def current_date_header() -> str:
    """Anchor line telling the model today's date so dates in a CV are judged
    relative to the real present (never assumed to be in the future)."""
    now = datetime.now(timezone.utc).strftime("%A, %d %B %Y")
    return f"CURRENT_DATE: {now}\n"
