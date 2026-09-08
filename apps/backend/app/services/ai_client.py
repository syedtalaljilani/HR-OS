import json
import urllib.request
import urllib.error

from app.core.config import settings

CHAT_TIMEOUT = 60
EMBED_TIMEOUT = 60
OCR_TIMEOUT = 180


class AIUnavailable(Exception):
    pass


def chat_json(messages: list[dict], model: str | None = None) -> dict:
    """Calls Ollama /api/chat with JSON format. Raises AIUnavailable on failure."""
    url = f"{settings.OLLAMA_URL}/api/chat"
    payload = {
        "model": model or settings.OLLAMA_MODEL,
        "messages": messages,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body.get("message", {}).get("content", "")
        return json.loads(content)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise AIUnavailable(str(e)) from e


def ocr_image(image_b64: str, hint: str = "Given the layout of the image.") -> str:
    """Run DeepSeek-OCR on a single image via Ollama. Raises AIUnavailable on failure."""
    url = f"{settings.OLLAMA_URL}/api/chat"
    payload = {
        "model": settings.OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": hint,
                "images": [image_b64],
            }
        ],
        "stream": False,
        "options": {"temperature": 0},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=OCR_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AIUnavailable(str(e)) from e
    return body.get("message", {}).get("content", "").strip()


def embed_text(text: str, model: str | None = None) -> list[float] | None:
    url = f"{settings.OLLAMA_URL}/api/embed"
    payload = {
        "model": model or settings.EMBEDDING_MODEL,
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
        with urllib.request.urlopen(req, timeout=EMBED_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        embeddings = body.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            return embeddings[0]
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