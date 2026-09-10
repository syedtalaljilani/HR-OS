"""Standalone Ollama client for the AI workflow.

Deliberately independent of the FastAPI backend so the workflow can be
reasoned about and tested on its own. Backend wrappers may reuse it.
"""
import json
import os
import urllib.error
import urllib.request

from ai.observability import current_generation

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-minilm")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "5m")

CHAT_TIMEOUT = 120
EMBED_TIMEOUT = 90


class AIUnavailable(Exception):
    """Raised when the LLM runtime cannot produce a structured response."""


def _request(url: str, payload: dict, timeout: int):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise AIUnavailable(str(e)) from e


def chat_json(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    keep_alive: str | None = None,
) -> dict:
    """Call Ollama /api/chat and return parsed JSON. Raises AIUnavailable."""
    options: dict = {"temperature": temperature}
    if max_tokens:
        options["num_predict"] = max_tokens
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "format": "json",
        "stream": False,
        "keep_alive": keep_alive or OLLAMA_KEEP_ALIVE,
        # Qwen3 emits long reasoning traces by default. For structured, time-boxed
        # HR work (CV parsing, screening, emails) the chain-of-thought is not
        # needed — disabling it cuts latency and token usage dramatically.
        "think": False,
        "options": options,
    }
    model_name = model or OLLAMA_MODEL
    with current_generation(
        name="ollama-chat",
        model=model_name,
        model_parameters={
            "temperature": temperature,
            "max_tokens": max_tokens,
            "keep_alive": keep_alive or OLLAMA_KEEP_ALIVE,
        },
        input={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    ) as gen:
        body = _request(f"{OLLAMA_URL}/api/chat", payload, CHAT_TIMEOUT)
        content = body.get("message", {}).get("content", "")
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise AIUnavailable(f"LLM returned invalid JSON: {e}") from e
        gen.update(output=result)
        return result


def embed_text(text: str, model: str | None = None) -> list[float] | None:
    """Return a single embedding vector, or None on failure."""
    payload = {
        "model": model or EMBEDDING_MODEL,
        "input": text[:8000],
        "truncate": True,
    }
    model_name = model or EMBEDDING_MODEL
    with current_generation(
        name="ollama-embed",
        model=model_name,
        input={"text": text[:2000], "truncate": True},
    ) as gen:
        try:
            body = _request(f"{OLLAMA_URL}/api/embed", payload, EMBED_TIMEOUT)
        except AIUnavailable:
            return None
        embeddings = body.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            vector = embeddings[0]
            # Do not log the full vector (hundreds of floats) into the trace.
            gen.update(
                output={
                    "dimensions": len(vector) if isinstance(vector, list) else None,
                    "embedded": True,
                }
            )
            return vector
        gen.update(output={"embedded": False})
        return None


def is_available() -> bool:
    try:
        url = f"{OLLAMA_URL}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
