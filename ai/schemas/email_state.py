"""LangGraph state for the email-writing workflow."""
from typing import Any

from pydantic import BaseModel, Field


class EmailAgentState(BaseModel):
    """State carried through the LangGraph email agent.

    Used both to draft pipeline emails (rejection/acceptance) and to assist an
    HR user in writing a custom email. The output is a ``draft`` dict with
    ``subject`` and ``body`` for human review before sending.
    """

    # Inputs
    email_type: str | None = None          # REJECTED / SELECTED / INTERVIEW / ...
    candidate_name: str | None = None
    job_title: str | None = None
    reason: str | None = None              # short rejection/decision reason
    context: dict[str, Any] = Field(default_factory=dict)  # score/rank/missing
    hr_notes: str | None = None            # free-form prompt from HR
    tone: str | None = None                # professional / warm / firm / custom
    company_name: str | None = None        # sender/company identity in the email
    hr_name: str | None = None             # sign-off / contact person

    # Node output
    draft: dict[str, Any] | None = None    # {subject, body}

    # Workflow control
    ai_mode: bool = True
    errors: list[str] = Field(default_factory=list)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    model: str | None = None

    def as_plain(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
