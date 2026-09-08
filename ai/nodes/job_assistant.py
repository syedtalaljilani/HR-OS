"""Job posting assistant node.

Turns a job title + user note/prompt into a draft job description using the
LLM. Deterministic fallback keeps partial output even when the model is
unavailable. Salary is not part of the draft — the hiring manager sets it.
"""
import re

from ai.prompts import job_assistant
from ai.schemas.job_state import JobAssistantState
from ._util import NodeError, llm_json


def _to_plain_text(value: str) -> str:
    lines = []
    for line in value.splitlines():
        stripped = line.strip()
        if re.match(r"^#{1,6}\s*", stripped):
            stripped = re.sub(r"^#{1,6}\s*", "", stripped)
        stripped = re.sub(r"^\s*(?:[*\-+]|\d+[.)])\s+", "", stripped)
        stripped = stripped.replace("**", "")
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def _fallback(job_title: str | None, user_note: str | None) -> dict:
    base = user_note or (f"Role for {job_title}" if job_title else "")
    return {
        "description": base,
    }


def run(state: JobAssistantState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions or {})
    model = state.model

    try:
        raw, prompt_versions, model = llm_json(
            job_assistant.SYSTEM,
            job_assistant.user(state.job_title, state.user_note),
            prompt_version=job_assistant.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        description = raw.get("description")
        draft = {
            "description": _to_plain_text(
                description if isinstance(description, str) else ""
            ),
        }
    except (NodeError, ValueError):
        errors.append("job_assistant: LLM failed, used deterministic fallback")
        draft = _fallback(state.job_title, state.user_note)

    return {
        "job_draft": draft,
        "errors": errors,
        "model": model,
    }
