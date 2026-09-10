"""Shared Langfuse observability for the AI workflow and the FastAPI backend.

Everything here no-ops when Langfuse is not configured (missing/invalid
credentials or ``LANGFUSE_ENABLED=false``), so existing behavior, background
workers and the fully-offline pytest suite are preserved.

Configuration (read from the repo-root ``.env``):

- ``LANGFUSE_PUBLIC_KEY`` / ``LANGFUSE_SECRET_KEY`` — project API keys
  (Langfuse UI: Project Settings -> API Keys).
- ``LANGFUSE_BASE_URL`` or ``LANGFUSE_HOST`` — self-hosted / cloud origin.
- ``LANGFUSE_ENABLED`` (default ``true``) — master switch, useful to disable
  tracing without removing credentials.
- ``LANGFUSE_DEBUG`` (default ``false``) — Langfuse SDK debug logging.
"""
import logging
import os
import threading
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _REPO_ROOT / ".env"

logger = logging.getLogger(__name__)

_langfuse: Optional[Any] = None
_langfuse_sdk_missing = False
_langfuse_lock = threading.Lock()


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE, override=False)
    except Exception:
        pass


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _configured() -> bool:
    if os.getenv("LANGFUSE_ENABLED", "true").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return False
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY")) and bool(
        os.getenv("LANGFUSE_SECRET_KEY")
    )


def get_langfuse():
    """Lazy singleton Langfuse client, or ``None`` when tracing is off."""
    global _langfuse, _langfuse_sdk_missing
    if _langfuse is not None or _langfuse_sdk_missing:
        return _langfuse
    with _langfuse_lock:
        if _langfuse is not None or _langfuse_sdk_missing:
            return _langfuse
        _load_env()
        if not _configured():
            return None
        try:
            from langfuse import Langfuse
        except ImportError:
            _langfuse_sdk_missing = True
            logger.warning(
                "Langfuse tracing disabled: credentials are set in .env but the "
                "'langfuse' package is not installed. Install it with "
                "`pip install langfuse` (pinned in apps/backend/requirements.txt)."
            )
            return None
        host = (
            os.getenv("LANGFUSE_HOST")
            or os.getenv("LANGFUSE_BASE_URL")
            or "http://localhost:3000"
        )
        _langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=host,
            debug=_env_flag("LANGFUSE_DEBUG"),
            environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or None,
        )
        return _langfuse


def langfuse_callbacks() -> list:
    """LangChain callback handlers for LangGraph runs ([] when disabled)."""
    if get_langfuse() is None:
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler()]


class _NoopObservation:
    """Drop-in stand-in so call sites can always use the same shape."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, **kwargs):
        return self

    def end(self):
        return None


def current_generation(*, name: str, input: Any = None, **attrs: Any) -> Any:
    """Context manager for an LLM ``generation`` observation on the active trace.

    Yields an object with ``.update(**kwargs)`` (or a no-op when disabled).
    """
    lf = get_langfuse()
    if lf is None:
        return nullcontext(_NoopObservation())
    return lf.start_as_current_observation(
        as_type="generation", name=name, input=input, **attrs
    )


def traced(name: str, **attrs: Any) -> Callable:
    """Decorate a function to open a trace (root span) named ``name``.

    Function args are never captured (they typically include DB sessions and
    ORM objects); call :func:`set_span_io` inside to record meaningful I/O.
    """

    def deco(fn: Callable) -> Callable:
        if get_langfuse() is None:
            return fn
        from langfuse import observe

        return observe(
            name=name,
            capture_input=False,
            capture_output=False,
            **attrs,
        )(fn)

    return deco


def set_span_io(*, input: Any = None, output: Any = None, metadata: Any = None) -> None:
    """Record input/output/metadata on the current (root) span of the trace."""
    lf = get_langfuse()
    if lf is None:
        return
    lf.update_current_span(
        input=input, output=output, metadata=metadata,
    )


def set_span_metadata(metadata: Any) -> None:
    """Attach metadata to the current span (merged with any existing value)."""
    lf = get_langfuse()
    if lf is None:
        return
    lf.update_current_span(metadata=metadata)


def invoke_graph(graph: Any, state: dict, **invoke_kwargs: Any) -> Any:
    """Run a compiled LangGraph with Langfuse tracing enabled.

    The LangChain callback handler turns every graph node into a span under
    the current trace (see the Langfuse LangChain/LangGraph integration); LLM
    generations traced inside the nodes via :func:`current_generation` nest
    under their node span.
    """
    callbacks = langfuse_callbacks()
    if callbacks and "config" not in invoke_kwargs:
        invoke_kwargs["config"] = {"callbacks": callbacks}
    elif callbacks:
        invoke_kwargs["config"] = {
            **invoke_kwargs["config"],
            "callbacks": callbacks,
        }
    return graph.invoke(state, **invoke_kwargs)