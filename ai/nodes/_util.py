"""Shared helpers for AI nodes."""
from ai.ollama import AIUnavailable, chat_json
from ai.schemas import ScreeningState


class NodeError(Exception):
    """Raised when a node cannot produce a usable output."""


def llm_json(
    system: str,
    prompt: str,
    *,
    prompt_version: str,
    model: str | None,
    prompt_versions: dict[str, str] | None = None,
    enabled: bool = True,
) -> tuple[dict, dict[str, str], str | None]:
    """Run an LLM node and record prompt/model versions.

    Returns ``(result, prompt_versions, model)`` so callers can persist the
    metadata through the LangGraph state (channels are last-value semantics).

    Raises ``NodeError`` when ``enabled`` is False so nodes fall back to
    deterministic logic (used for offline/degraded runs).
    """
    from ai.ollama import OLLAMA_MODEL

    versions = dict(prompt_versions or {})
    versions[prompt_version.split("-")[0]] = prompt_version
    model_ref = model or "ollama/" + OLLAMA_MODEL
    model_name = model_ref.split("/", 1)[-1]

    if not enabled:
        raise NodeError("ai_mode disabled; deterministic fallback requested")

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    try:
        result = chat_json(messages, model=model_name)
    except AIUnavailable as e:
        raise NodeError(f"AI unavailable: {e}") from e

    if not isinstance(result, dict):
        raise NodeError("LLM returned a non-object response")
    return result, versions, model_ref