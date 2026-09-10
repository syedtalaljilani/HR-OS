"""Minimal Langfuse public-API access for the evaluation harness.

Read-only trace/observation fetching plus score ingestion. Kept dependency-free
so the harness runs anywhere the backend settings resolve.
"""
import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings

_TIMEOUT = 30


def _credentials() -> tuple[str, str, str]:
    base = (
        getattr(settings, "LANGFUSE_BASE_URL", "")
        or os.getenv("LANGFUSE_BASE_URL", "")
        or "http://localhost:3000"
    ).rstrip("/")
    public = getattr(settings, "LANGFUSE_PUBLIC_KEY", "") or os.getenv(
        "LANGFUSE_PUBLIC_KEY", ""
    )
    secret = getattr(settings, "LANGFUSE_SECRET_KEY", "") or os.getenv(
        "LANGFUSE_SECRET_KEY", ""
    )
    return base, public, secret


def _headers() -> dict:
    _, public, secret = _credentials()
    token = base64.b64encode(f"{public}:{secret}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def _get(path: str) -> Any:
    base, _, _ = _credentials()
    req = urllib.request.Request(
        f"{base}{path}",
        headers=_headers(),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Langfuse GET {path} failed: {e}") from e


def _post(path: str, payload: dict) -> dict:
    base, _, _ = _credentials()
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Langfuse POST {path} failed: {e}") from e


def list_traces(limit: int = 50) -> list[dict]:
    """Return the most recent traces (metadata only) up to ``limit``."""
    page = 1
    out: list[dict] = []
    while len(out) < limit:
        batch = _get(f"/api/public/traces?limit=50&page={page}")
        data = batch.get("data") or []
        out.extend(data)
        if len(out) >= int(batch.get("meta", {}).get("totalItems", 0)) or not data:
            break
        page += 1
    return out[:limit]


def get_trace(trace_id: str) -> dict:
    """Fetch a full trace including its nested observations."""
    return _get(f"/api/public/traces/{trace_id}")


def ingest_score(trace_id: str, name: str, value: float, comment: str = "") -> None:
    """Ingest a numeric score (0-1) for a trace into Langfuse."""
    payload: dict[str, Any] = {"traceId": trace_id, "name": name, "value": value}
    if comment:
        payload["comment"] = comment
    _post("/api/public/scores", payload)


def judge_model() -> str:
    configured = getattr(settings, "EVAL_JUDGE_MODEL", "") or os.getenv(
        "EVAL_JUDGE_MODEL", ""
    )
    return configured or settings.OLLAMA_MODEL