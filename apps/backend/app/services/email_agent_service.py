"""Adapter that runs the LangGraph email agent.

The `ai` package lives at the repository root. The FastAPI backend runs from
`apps/backend`, so we make the repo root importable here.
"""
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.orm import Session

from ai.graphs.email import graph
from ai.schemas.email_state import EmailAgentState

from app.core.config import settings
from app.core.observability import invoke_graph, set_span_io, traced
from app.services import settings_service


def _identity(db: Session | None) -> tuple[str, str, str]:
    """(company_name, hr_name, company_location) from DB when available;
    env is the fallback."""
    if db is not None:
        try:
            return settings_service.org_identity(db)
        except Exception:
            pass
    return settings.COMPANY_NAME, settings.HR_NAME, settings.COMPANY_LOCATION


_TOKEN_PAIRS = [
    ("{COMPANY_NAME}", "company_name"),
    ("[COMPANY_NAME]", "company_name"),
    ("{HR_NAME}", "hr_name"),
    ("[HR_NAME]", "hr_name"),
]


def _clean_placeholders(
    body: str,
    company_name: str | None,
    hr_name: str | None,
) -> str:
    """Deterministically finalize the sign-off.

    Small models occasionally echo the prompt examples as literal
    "{COMPANY_NAME}" / "{HR_NAME}" (or "[COMPANY_NAME]") placeholders. Replace
    them with the real identity; when a name is missing, drop the placeholder
    and tidy any dangling artifact such as "on behalf of ".
    """
    if not body:
        return body
    values = {"company_name": company_name or "", "hr_name": hr_name or ""}
    for token, key in _TOKEN_PAIRS:
        body = body.replace(token, values[key])
    if not company_name:
        body = re.sub(r"(?i)[ \t]*on behalf of[ \t]*\.?[ \t]*", "", body)
    if not hr_name:
        body = re.sub(r"(?i)Best regards,[ \t]*$", "Best regards", body)
    body = re.sub(r"[\[\{\(][A-Z][A-Z0-9_ ]*[\]\}\)]", "", body)
    body = body.replace(",\n", "\n")
    body = re.sub(r"[ \t]{2,}", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _run(state: EmailAgentState) -> dict:
    """Run the email graph and return {subject, body, model}."""
    result = invoke_graph(graph, state.as_plain())
    draft = result.get("draft") or {}
    body = _clean_placeholders(draft.get("body", ""), state.company_name, state.hr_name)
    set_span_io(
        output={
            "subject": draft.get("subject", ""),
            "body": body,
            "model": result.get("model"),
        }
    )
    return {
        "subject": draft.get("subject", ""),
        "body": body,
        "model": result.get("model"),
    }


def _base_state(
    *,
    email_type: str | None,
    candidate_name: str | None,
    job_title: str | None,
    reason: str | None,
    context: dict | None,
    hr_notes: str | None,
    tone: str | None,
    db: Session | None = None,
) -> EmailAgentState:
    """Shared state: email drafting runs on the dedicated tiny EMAIL_MODEL and
    signs off with the configured company / HR identity (DB first, env fallback)."""
    company_name, hr_name, _ = _identity(db)
    return EmailAgentState(
        email_type=email_type,
        candidate_name=candidate_name,
        job_title=job_title,
        reason=reason,
        context=context or {},
        hr_notes=hr_notes,
        tone=tone,
        company_name=company_name or None,
        hr_name=hr_name or None,
        ai_mode=True,
        model=f"ollama/{settings.EMAIL_MODEL}",
    )


@traced("email-draft")
def draft_email(
    *,
    email_type: str | None = None,
    candidate_name: str | None = None,
    job_title: str | None = None,
    reason: str | None = None,
    context: dict | None = None,
    hr_notes: str | None = None,
    tone: str | None = None,
    db: Session | None = None,
) -> dict:
    """Draft a recruitment email (subject + body) using the dedicated email model.

    ``db`` optionally provides the company/HR identity from Settings; otherwise
    the environment fallback values are used.

    Returns a dict shaped like:
        {"subject": str, "body": str, "model": str | None}
    The draft is NOT persisted here �?" the caller reviews then sends.
    """
    state = _base_state(
        email_type=email_type,
        candidate_name=candidate_name,
        job_title=job_title,
        reason=reason,
        context=context,
        hr_notes=hr_notes,
        tone=tone,
        db=db,
    )
    return _run(state)


@traced("email-draft")
def assist_hr_email(
    *,
    hr_notes: str,
    candidate_name: str | None = None,
    job_title: str | None = None,
    email_type: str | None = None,
    tone: str | None = None,
    db: Session | None = None,
) -> dict:
    """HR email-writing assistant. Turns free-form HR notes into a draft."""
    state = _base_state(
        email_type=email_type,
        candidate_name=candidate_name,
        job_title=job_title,
        reason=None,
        context=None,
        hr_notes=hr_notes,
        tone=tone,
        db=db,
    )
    return _run(state)
