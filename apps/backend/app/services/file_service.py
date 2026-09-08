import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


def _sanitize_filename(filename: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return filename.strip("._") or "file"


def save_cv(file: UploadFile, contents: bytes) -> tuple[str, str]:
    base_dir = Path(settings.UPLOAD_DIR) / "cvs"
    base_dir.mkdir(parents=True, exist_ok=True)

    suffix = ""
    if file.filename:
        suffix = Path(file.filename).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = base_dir / stored_name
    dest.write_bytes(contents)

    mime_type = file.content_type or ""
    if not mime_type and suffix == ".pdf":
        mime_type = "application/pdf"
    return str(dest).replace("\\", "/"), mime_type