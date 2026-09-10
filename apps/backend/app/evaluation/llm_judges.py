"""LLM-as-a-judge evaluators for the app's LLM features.

Judges run on the local Ollama model (``EVAL_JUDGE_MODEL``, defaulting to the
general model) and deliberately bypass Langfuse tracing so evaluation runs do
not pollute the trace history. Every judge returns a 0-1 score plus a short
human-readable reason, extracted from the LLM's structured 0-10 rating.
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings

from .lf_api import judge_model

_TIMEOUT = 120


def _judge_chat(system: str, user: str, max_tokens: int = 1500) -> dict:
    """One untraced structured (JSON) LLM call for a judge."""
    payload = {
        "model": judge_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": "json",
        "stream": False,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "think": False,
        "options": {"temperature": 0.0, "num_predict": max_tokens},
    }
    req = urllib.request.Request(
        f"{settings.OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body.get("message", {}).get("content", "")
        result = json.loads(content)
        return result if isinstance(result, dict) else {}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return {}


def _score(value: Any) -> float | None:
    """Map a 0-10 rating (maybe a string or out-of-range int) to 0-1."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return round(max(0.0, min(1.0, num / 10.0)), 3)


def _check(result: dict, key: str) -> float | None:
    return _score(result.get(key))


def _reason(result: dict, key: str) -> str:
    reason = result.get(f"{key}_reason") or result.get("reason") or ""
    return str(reason).strip()[:400]


def judge_extraction(cv_text: str, profile: dict) -> dict[str, dict]:
    """faithfulness: fields traceable to the CV; completeness: sections kept."""
    system = (
        "You are a strict data-quality judge for CV extraction by an AI assistant. "
        "Compare the EXTRACTED PROFILE against the SOURCE CV TEXT and rate two "
        "dimensions from 0 to 10:\n"
        "- faithfulness: 10 means every field is traceable to the CV with no "
        "fabricated facts; 0 means the profile invents content not in the CV.\n"
        "- completeness: 10 means all meaningful sections present in the CV "
        "(skills, experience, education, projects, certifications...) were "
        "preserved; 0 means most were dropped, emptied or summarized away.\n"
        "Return ONLY JSON:\n"
        '{"faithfulness": 0..10, "faithfulness_reason": "...", '
        '"completeness": 0..10, "completeness_reason": "..."}'
    )
    user = (
        "SOURCE CV TEXT:\n"
        f"{cv_text[:12000]}\n\n"
        "EXTRACTED PROFILE (JSON):\n"
        f"{json.dumps(profile, ensure_ascii=False)[:6000]}"
    )
    result = _judge_chat(system, user)
    return {
        "extraction_faithfulness": {
            "value": _check(result, "faithfulness"),
            "comment": _reason(result, "faithfulness"),
        },
        "extraction_completeness": {
            "value": _check(result, "completeness"),
            "comment": _reason(result, "completeness"),
        },
    }


def judge_screening(matched: list[dict], recommendation: dict) -> dict[str, dict]:
    """evidence_soundness: do score/recommendation follow from the match table."""
    system = (
        "You are a strict judge of an AI CV-screening decision. You are given "
        "the requirement match table (requirement, status MATCH/PARTIAL/MISSING/"
        "UNCLEAR, evidence excerpt) and the final recommendation (score 0-100, "
        "label, reason).\n"
        "Rate from 0 to 10 how well the recommendation follows from the match "
        "table: 10 means the score, label and reason are fully justified by the "
        "evidence (e.g. MISSING mandatory requirements cannot produce a strong "
        "recommendation, and UNCLEAR items must be acknowledged); 0 means the "
        "decision contradicts its own evidence.\n"
        "Return ONLY JSON:\n"
        '{"evidence_soundness": 0..10, "evidence_soundness_reason": "..."}'
    )
    user = json.dumps(
        {"matched_requirements": matched[:40], "recommendation": recommendation},
        ensure_ascii=False,
        default=str,
    )[:12000]
    result = _judge_chat(system, user)
    return {
        "screening_soundness": {
            "value": _check(result, "evidence_soundness"),
            "comment": _reason(result, "evidence_soundness"),
        },
    }


def judge_job_draft(job_title: str | None, user_note: str, description: str) -> dict[str, dict]:
    """note_coverage: does the draft cover what the hiring manager asked for."""
    system = (
        "You are a strict judge of a job-description draft written by an AI "
        "assistant from a hiring manager's note. Rate from 0 to 10 how well the "
        "draft covers the manager's request: 10 means every requirement, duty or "
        "detail in the note is reflected and the role is concrete; 0 means the "
        "draft ignores the note almost entirely.\n"
        "Return ONLY JSON:\n"
        '{"note_coverage": 0..10, "note_coverage_reason": "..."}'
    )
    user = (
        f"JOB TITLE: {job_title or '(none)'}\n\n"
        f"MANAGER NOTE:\n{user_note[:6000]}\n\n"
        f"DRAFT DESCRIPTION:\n{description[:12000]}"
    )
    result = _judge_chat(system, user)
    return {
        "job_draft_coverage": {
            "value": _check(result, "note_coverage"),
            "comment": _reason(result, "note_coverage"),
        },
    }


def judge_email(task_context: str, subject: str, body: str) -> dict[str, dict]:
    """tone: appropriateness; completeness: purpose + recipient handled."""
    system = (
        "You are a strict judge of recruitment emails drafted by an AI assistant "
        "from a task description. Rate two dimensions from 0 to 10:\n"
        "- tone: 10 means professional, warm-but-formal, appropriate to the "
        "email type (rejection, selection, scheduling, reply); 0 means rude, "
        "flippant, or clearly wrong for the situation.\n"
        "- completeness: 10 means the email serves its purpose, addresses the "
        "recipient by name where needed, and any promised next step is clear; 0 "
        "means it omits the purpose or key facts.\n"
        "Return ONLY JSON:\n"
        '{"tone": 0..10, "tone_reason": "...", "completeness": 0..10, '
        '"completeness_reason": "..."}'
    )
    user = (
        f"EMAIL TASK:\n{task_context[:6000]}\n\n"
        f"SUBJECT:\n{subject}\n\n"
        f"BODY:\n{body[:12000]}"
    )
    result = _judge_chat(system, user)
    return {
        "email_tone": {
            "value": _check(result, "tone"),
            "comment": _reason(result, "tone"),
        },
        "email_completeness": {
            "value": _check(result, "completeness"),
            "comment": _reason(result, "completeness"),
        },
    }