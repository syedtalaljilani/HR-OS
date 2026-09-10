import json
import urllib.request
import urllib.error

from app.core.config import settings
from app.core.observability import current_generation

CHAT_TIMEOUT = 60
EMBED_TIMEOUT = 60


class AIUnavailable(Exception):
    pass


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
    payload = {
        "model": model_name,
        "messages": messages,
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
    try:
        with current_generation(
            name="ollama-chat",
            model=model_name,
            model_parameters={"temperature": temperature, "max_tokens": max_tokens},
            input={
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        ) as gen:
            with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = body.get("message", {}).get("content", "")
            result = json.loads(content)
            gen.update(output=result)
        return result
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise AIUnavailable(str(e)) from e


def embed_text(text: str, model: str | None = None) -> list[float] | None:
    url = f"{settings.OLLAMA_URL}/api/embed"
    model_name = model or settings.EMBEDDING_MODEL
    payload = {
        "model": model_name,
        "input": text[:8000],
        "truncate": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with current_generation(
            name="ollama-embed",
            model=model_name,
            input={"text": text[:2000], "truncate": True},
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
                    }
                )
                return vector
            gen.update(output={"embedded": False})
            return None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
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
                }
            )
            return text
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise AIUnavailable(str(e)) from e