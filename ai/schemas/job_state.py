"""LangGraph state for the job-posting assistant workflow."""
from typing import Any

from pydantic import BaseModel, Field


class JobAssistantState(BaseModel):
    """State carried through the LangGraph job-posting assistant."""

    # Inputs
    job_title: str | None = None
    user_note: str | None = None

    # Node output
    job_draft: dict[str, Any] | None = None

    # Workflow control
    ai_mode: bool = True
    errors: list[str] = Field(default_factory=list)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    model: str | None = None

    def as_plain(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
