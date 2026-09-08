from datetime import datetime

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def validate_cv_file(file: UploadFile) -> None:
    extension = ""
    if file.filename:
        extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    ext = f".{extension}" if extension else ""

    if ext not in settings.ALLOWED_CV_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_CV_EXTENSIONS)}",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in settings.ALLOWED_CV_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type: {content_type or 'unknown'}",
        )


def validate_file_size(contents: bytes) -> None:
    max_bytes = settings.MAX_CV_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_CV_SIZE_MB} MB",
        )


def datetime_from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None