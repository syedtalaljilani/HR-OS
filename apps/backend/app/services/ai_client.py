import json
import logging
import time
import urllib.request
import urllib.error

from app.core.ai_guardrails import sanitize_ai_text
from app.core.config import settings
from app.core.observability import current_generation

CHAT_TIMEOUT = 60
EMBED_TIMEOUT = 60

logger = logging.getLogger("hros.llm")


class AIUnavailable(Exception):
    pass


def _usage_details(body: dict) -> dict | None:
    """Map Ollama token counts to Langfuse ``usage_details`` (input/output)."""
    details: dict = {}
    if body.get("prompt_eval_count") is not None:
        details["input"] = body["prompt_eval_count"]
    if body.get("eval_count") is not None:
        details["output"] = body["eval_count"]
    return details or None


def _sanitize_messages(messages: list[dict]) -> list[dict]:
    """Sanitize + bound every text message before it reaches the model."""
    out: list[dict] = []
    for msg in messages:
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            msg = {**msg, "content": sanitize_ai_text(msg["content"])}
        out.append(msg)
    return out


def chat_json(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.1,
) -> dict:
    """Calls Ollama /api/chat with JSON format. Raises AIUnavailable on failure."""
    url = f"{settings.OLLAMA_URL}/api/chat"
    options: dict = {"temperature": temperature}
    if max_tokens:
        options["num_predict"] = max_tokens
    model_name = model or settings.OLLAMA_MODEL
    sanitized = _sanitize_messages(messages)
    payload = {
        "model": model_name,
        "messages": sanitized,
        "format": "json",
        "stream": False,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        # Qwen3 reasons by default; structured HR tasks do not need the CoT,
        # and disabling it makes screening/CV parsing far faster.
        "think": False,
        "options": options,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = _monotonic_ms()
    try:
        with current_generation(
            name="ollama-chat",
            model=model_name,
            model_parameters={"temperature": temperature, "max_tokens": max_tokens},
            input={
                "messages": sanitized,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        ) as gen:
            with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = body.get("message", {}).get("content", "")
            result = json.loads(content)
            gen.update(output=result, usage_details=_usage_details(body))
        logger.info(
            "llm.chat model=%s prompt_tokens=%s completion_tokens=%s dur_ms=%d",
            model_name,
            body.get("prompt_eval_count"),
            body.get("eval_count"),
            _monotonic_ms() - start,
        )
        return result
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        logger.warning(
            "llm.chat model=%s failed err=%s dur_ms=%d",
            model_name,
            str(e)[:200],
            _monotonic_ms() - start,
        )
        raise AIUnavailable(str(e)) from e


def _monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def embed_text(text: str, model: str | None = None) -> list[float] | None:
    url = f"{settings.OLLAMA_URL}/api/embed"
    model_name = model or settings.EMBEDDING_MODEL
    safe_text = sanitize_ai_text(text, max_chars=8000)
    payload = {
        "model": model_name,
        "input": safe_text,
        "truncate": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = _monotonic_ms()
    try:
        with current_generation(
            name="ollama-embed",
            model=model_name,
            input={"text": safe_text[:2000], "truncate": True},
        ) as gen:
            with urllib.request.urlopen(req, timeout=EMBED_TIMEOUT) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            embeddings = body.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                vector = embeddings[0]
                gen.update(
                    output={
                        "dimensions": len(vector) if isinstance(vector, list) else None,
                        "embedded": True,
                    },
                    usage_details=_usage_details(body),
                )
                logger.info(
                    "llm.embed model=%s prompt_tokens=%s dur_ms=%d",
                    model_name,
                    body.get("prompt_eval_count"),
                    _monotonic_ms() - start,
                )
                return vector
            gen.update(output={"embedded": False}, usage_details=_usage_details(body))
            logger.info("llm.embed model=%s no_embeddings dur_ms=%d", model_name, _monotonic_ms() - start)
            return None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        logger.warning("llm.embed model=%s failed dur_ms=%d", model_name, _monotonic_ms() - start)
        return None


def is_available() -> bool:
    try:
        url = f"{settings.OLLAMA_URL}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ocr_images(images_b64: list[str], model: str | None = None) -> str:
    """Run vision OCR over one or more page images via /api/chat.

    All pages are sent in a single request (one model call, no per-page
    round-trips). Raises AIUnavailable on any failure so callers can fall
    back to the previous behavior.
    """
    if not images_b64:
        raise AIUnavailable("No page images to OCR")
    url = f"{settings.OLLAMA_URL}/api/chat"
    model_name = model or settings.OLLAMA_OCR_MODEL
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": (
                    "You are an OCR engine for resumes/CVs. Extract ALL visible "
                    "text from every image provided, page by page, in the order "
                    "they are given. Preserve line breaks, headings and sections "
                    "so the text can be re-parsed. Return the plain text of all "
                    "pages with no commentary, no preamble and no markdown "
                    "fences."
                ),
                "images": images_b64,
            }
        ],
        "stream": False,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": {"temperature": 0.0, "num_predict": 8192},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with current_generation(
            name="ollama-ocr",
            model=model_name,
            input={
                # Page images are base64 and never captured in full; only
                # metadata about the payload is recorded.
                "model": model_name,
                "page_count": len(images_b64),
                "page_images_omitted": True,
            },
            model_parameters={"num_predict": 8192},
        ) as gen:
            with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT * 3) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            text = (body.get("message", {}).get("content") or "").strip()
            gen.update(
                output={
                    "text": text,
                    "char_count": len(text),
                },
                usage_details=_usage_details(body),
            )
            return text
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise AIUnavailable(str(e)) from e