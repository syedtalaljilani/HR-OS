"""Centralized structured logging for the backend.

Sets up the shared ``hros`` logger tree (all services log under ``hros.*``)
with a console handler (and optional rotating file handler). Every record is
decorated with a ``request_id`` bound from a context variable so logs can be
correlated across a single HTTP request / background tick.

Usage:
    from app.core.logging import configure_logging, bind_request_id, get_logger

    configure_logging()          # once at app startup
    get_logger("hros.applications").info("created application %s", app_id)

No log handler ever writes request/response bodies or AI payloads — only
metadata (method, path, status, duration, ids).
"""
import json
import logging
import logging.handlers
import uuid
from contextvars import ContextVar

from app.core.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

_configured = False


class RequestIdFilter(logging.Filter):
    """Injects the current ``request_id`` into every emitted log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


def _formatter() -> logging.Formatter:
    if settings.LOG_JSON:
        return _JsonFormatter()
    return logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s request_id=%(request_id)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


class _JsonFormatter(logging.Formatter):
    """Minimal JSON-lines formatter (safe for file/aggregator ingestion)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        extras = getattr(record, "extra", None)
        if isinstance(extras, dict):
            payload.update(extras)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Idempotently wire handlers onto the shared ``hros`` logger tree."""
    global _configured
    if _configured:
        return
    _configured = True

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    tree = logging.getLogger("hros")
    tree.setLevel(level)
    # Stop at this tree so records are not echoed again by the root logger
    # (uvicorn configures the root with its own handlers).
    tree.propagate = False

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(_formatter())
    console.addFilter(RequestIdFilter())
    tree.addHandler(console)

    if settings.LOG_FILE:
        try:
            from pathlib import Path

            Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=5_000_000,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(_formatter())
            file_handler.addFilter(RequestIdFilter())
            tree.addHandler(file_handler)
        except OSError:
            # Never let logging failures take the app down.
            logging.getLogger("hros").warning(
                "Could not open LOG_FILE %s; continuing with console only",
                settings.LOG_FILE,
            )


def bind_request_id(request_id: str | None = None) -> tuple[str, object]:
    """Set the request-id context for the current async task / thread.

    Returns ``(request_id, token)`` so the caller can ``reset(token)`` on exit.
    Mirrors the parent/source header when provided, else generates a short id.
    """
    rid = (request_id or "").strip() or uuid.uuid4().hex[:16]
    token = request_id_var.set(rid)
    return rid, token


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class RequestLoggingMiddleware:
    """Pure-ASGI middleware: binds a request id, times the call, logs it.

    Adds/re-emits ``X-Request-ID`` on the response so a failing request can be
    traced from browser to log line. Never buffers or logs request bodies.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_headers = dict(scope.get("headers") or [])
        parent = raw_headers.get(b"x-request-id", b"").decode("ascii", "ignore").strip()
        rid, token = bind_request_id(parent or None)

        logger = get_logger("hros.request")
        client = scope.get("client")
        method = scope.get("method", "")
        path = scope.get("path", "")
        start = _monotonic_ms()
        status = ["-"]

        async def _send(message):
            if message.get("type") == "http.response.start":
                status[0] = str(message.get("status", "-"))
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", rid.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception:
            logger.exception(
                "%s %s -> unhandled error (%d ms) client=%s",
                method,
                path,
                round(_monotonic_ms() - start),
                f"{client[0]}:{client[1]}" if client else "-",
                extra={"method": method, "path": path, "status": status[0]},
            )
            raise
        finally:
            duration = round(_monotonic_ms() - start)
            logger.info(
                "%s %s -> %s (%d ms) client=%s",
                method,
                path,
                status[0],
                duration,
                f"{client[0]}:{client[1]}" if client else "-",
                extra={"method": method, "path": path, "status": status[0], "duration_ms": duration},
            )
            request_id_var.reset(token)


def _monotonic_ms() -> int:
    import time

    return int(time.monotonic() * 1000)