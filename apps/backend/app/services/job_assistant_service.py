"""Adapter that runs the LangGraph job-posting assistant.

The `ai` package lives at the repository root. The FastAPI backend runs from
`apps/backend`, so we make the repo root importable here.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai.graphs.job_assistant import graph
from ai.schemas.job_state import JobAssistantState


def generate_job_draft(job_title: str | None, user_note: str) -> dict:
    """Run the LangGraph assistant and return a draft for human review.

    Returns a dict shaped like:
        {
            "description": str,
            "salary_min": int | None,
            "salary_max": int | None,
            "model": str | None,
        }
    The draft is NOT persisted here — the caller reviews then saves.
    """
    state = JobAssistantState(
        job_title=job_title,
        user_note=user_note,
        ai_mode=True,
    )
    result = graph.invoke(state.as_plain())
    draft = result.get("job_draft") or {}
    return {
        "description": draft.get("description", ""),
        "salary_min": draft.get("salary_min"),
        "salary_max": draft.get("salary_max"),
        "model": result.get("model"),
    }
