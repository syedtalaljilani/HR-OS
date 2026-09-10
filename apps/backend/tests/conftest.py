"""Hermetic test configuration.

Pin `LANGFUSE_ENABLED=false` (and clear the keys) before the app imports so
every observability helper degrades to its no-op path. Tests stay fully offline
and never attempt to reach a Langfuse/Ollama server, regardless of what is in
the developer .env.
"""
import os
from pathlib import Path

os.environ.setdefault("LANGFUSE_ENABLED", "false")
os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
os.environ.pop("LANGFUSE_SECRET_KEY", None)
os.environ.pop("LANGFUSE_BASE_URL", None)

# Keep the backend's `.env` from re-enabling tracing via load_dotenv(override=False).
_ENV_SWITCH = Path(__file__).resolve()
if os.environ.get("LANGFUSE_ENABLED") != "false":
    os.environ["LANGFUSE_ENABLED"] = "false"
