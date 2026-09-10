"""Backend-facing re-export of the shared Langfuse observability helpers.

The ``ai`` package lives at the repository root while the FastAPI app runs
from ``apps/backend``, so the repo root is made importable here first (same
pattern as the LangGraph service adapters in ``app/services``).
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai.observability import (  # noqa: E402,F401
    current_generation,
    get_langfuse,
    invoke_graph,
    langfuse_callbacks,
    set_span_io,
    traced,
)

__all__ = [
    "current_generation",
    "get_langfuse",
    "invoke_graph",
    "langfuse_callbacks",
    "set_span_io",
    "traced",
]