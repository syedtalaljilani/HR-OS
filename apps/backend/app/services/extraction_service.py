import base64
import hashlib
import io
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import set_span_io, traced
from app.db.models.application import CVDocument
from app.db.models.candidate import Candidate
from app.db.models.enums import ExtractionStatus
from app.db.models.job import Job
from app.services import ai_client

_PROFILE_CACHE_TTL_SECONDS = 3600
_PROFILE_CACHE: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_PROFILE_CACHE_LOCK = threading.Lock()

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "sql", "postgresql",
    "mongodb", "redis", "fastapi", "django", "flask", "react", "nextjs", "node",
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "pandas", "numpy",
    "machine learning", "deep learning", "llm", "nlp", "devops", "ci/cd",
    "microservices", "rest api", "graphql", "html", "css", "tailwind",
]


def _resolve_path(file_path: str) -> Path:
    p = Path(file_path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


def extract_text_from_cv(cv: CVDocument) -> str:
    path = _resolve_path(cv.file_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CV file not found on disk"
        )
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages
            ).strip()
        if suffix == ".docx":
            from docx import Document

            doc = Document(str(path))
            lines = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    lines.extend(cell.text for cell in row.cells)
            return "\n".join(lines).strip()
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore").strip()
        if suffix == ".doc":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Legacy .doc files are not supported; please upload .docx or PDF",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read any text from this CV. The file may be "
            "corrupt or password-protected. Please upload a valid CV file.",
        )
    raise HTTPException(status_code=400, detail="Unsupported CV file type")


def extract_text_from_cv_bytes(contents: bytes, filename: str) -> str:
    """Extract the embedded text layer from an in-memory CV (PDF/DOCX/TXT).

    Raises HTTPException(400) when the file type is unsupported or the file
    is corrupt/unreadable, so public (unauthenticated) routes never leak a 500.
    """
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(contents))
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages
            ).strip()
        if suffix == ".docx":
            from docx import Document

            doc = Document(io.BytesIO(contents))
            lines = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    lines.extend(cell.text for cell in row.cells)
            return "\n".join(lines).strip()
        if suffix == ".txt":
            return contents.decode("utf-8", errors="ignore").strip()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read any text from this CV. The file may be "
            "corrupt or password-protected. Please upload a valid CV file.",
        )
    raise HTTPException(status_code=400, detail="Unsupported CV file type")


def _render_pdf_pages_base64(contents: bytes) -> list[str]:
    """Render the first few pages of a PDF to PNGs (base64) for OCR.

    Uses PyMuPDF so no external poppler/PIL dependency is needed. Returns an
    empty list if the PDF cannot be rasterized.
    """
    try:
        import pymupdf

        doc = pymupdf.open(stream=contents, filetype="pdf")
    except Exception:
        return []
    try:
        pages: list[str] = []
        last = min(len(doc), max(1, settings.OCR_MAX_PAGES))
        for page_index in range(last):
            try:
                page = doc[page_index]
                pix = page.get_pixmap(dpi=max(72, int(settings.OCR_DPI)))
                pages.append(base64.b64encode(pix.tobytes("png")).decode("ascii"))
            except Exception:
                continue
        return pages
    finally:
        try:
            doc.close()
        except Exception:
            pass


def ocr_text_from_pdf(contents: bytes) -> str:
    """OCR a scanned/image PDF via the local vision model (deepseek-ocr).

    Pages are rendered and processed ONE image per model call: batched
    multi-image requests make deepseek-ocr degenerate into chat-template
    tokens instead of text. Raises ``AIUnavailable`` when OCR cannot be
    produced so callers keep their existing fallback behavior.
    """
    from app.services import ai_client

    pages = _render_pdf_pages_base64(contents)
    if not pages:
        raise ai_client.AIUnavailable("Could not rasterize PDF pages for OCR")
    sections: list[str] = []
    for page_index, page in enumerate(pages, start=1):
        text = ai_client.ocr_images([page], model=settings.OLLAMA_OCR_MODEL)
        text = _strip_ocr_markers(text)
        if text:
            sections.append(f"[Page {page_index}]\n{text}")
    return "\n\n".join(sections).strip()


def _strip_ocr_markers(text: str) -> str:
    """Drop DeepSeek-OCR branch/marker lines and normalize whitespace."""
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if (
            "<|" in line
            or line.startswith("#")
            or re.fullmatch(r"[#*_\-=|]+\s*", line)
        ):
            continue
        kept.append(re.sub(r"\s{2,}", " ", line))
    return "\n".join(kept).strip()


def _fallback_extract_profile(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email = next(
        (m.group(0) for ln in lines for m in [re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", ln)] if m),
        None,
    )
    phone = None
    for ln in lines:
        m = re.search(r"(\+?\d[\d\s().-]{7,}\d)", ln)
        if m:
            phone = m.group(0).strip()
            break

    name = None
    for ln in lines[:6]:
        if email and email in ln:
            continue
        if len(ln) < 60 and not re.search(r"\d", ln):
            name = ln
            break

    low_text = text.lower()
    skills = [s for s in SKILL_KEYWORDS if s in low_text]

    education = []
    for keyword in ("bachelor", "master", "phd", "bs ", "ms ", "b.s.", "m.s.", "degree", "university", "college"):
        if keyword in low_text:
            education.append(keyword.strip())
    education = list(dict.fromkeys(education))[:5]

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "education": [e.title() for e in education],
    }


def extract_candidate_profile(text: str) -> dict:
    try:
        result = ai_client.chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You extract structured candidate data from a CV. "
                        "Return ONLY JSON with these keys: "
                        "name, email, phone, address, expected_salary (string or null), "
                        "summary (one short professional summary sentence or null), "
                        "skills (array of plain skill names), "
                        "languages (array of languages), interests (array), "
                        "links (array of profile URLs), "
                        "education (array of objects with degree, institution, years), "
                        "experience (array of objects with position, company, years, description), "
                        "projects (array of objects with name, link, description), "
                        "certifications (array of objects with name, issuer, year), "
                        "publications (array of objects with title, publisher, year). "
                        "Preserve every meaningful entry in the CV — do not skip or "
                        "summarize lists. If a value is unknown use null. If a section "
                        "does not exist in the CV use an empty array."
                    ),
                },
                {"role": "user", "content": text[:30000]},
            ],
            model=settings.OLLAMA_PROFILE_MODEL or settings.OLLAMA_MODEL,
            max_tokens=3000,
            temperature=0.0,
        )
        if isinstance(result, dict):
            scalar_keys = ("name", "email", "phone", "address", "expected_salary", "summary")
            list_keys = ("skills", "languages", "interests", "links")
            object_keys = (
                "education",
                "experience",
                "projects",
                "certifications",
                "publications",
            )
            for key in scalar_keys:
                if key not in result:
                    result[key] = None
            for key in list_keys:
                value = result.get(key)
                if isinstance(value, str):
                    result[key] = [
                        part.strip() for part in re.split(r"[,;]", value) if part.strip()
                    ]
                elif not isinstance(value, list):
                    result[key] = []
            for key in object_keys:
                value = result.get(key)
                if isinstance(value, str):
                    result[key] = []
                elif isinstance(value, list):
                    result[key] = [
                        item
                        for item in value
                        if isinstance(item, dict)
                        or (isinstance(item, str) and item.strip())
                    ]
                else:
                    result[key] = []
            return result
    except ai_client.AIUnavailable:
        pass
    except (TimeoutError, OSError):
        pass
    return _fallback_extract_profile(text)


def _cache_get(key: str) -> dict | None:
    with _PROFILE_CACHE_LOCK:
        item = _PROFILE_CACHE.get(key)
        if item is None:
            return None
        timestamp, value = item
        if time.time() - timestamp > _PROFILE_CACHE_TTL_SECONDS:
            _PROFILE_CACHE.pop(key, None)
            return None
        _PROFILE_CACHE.move_to_end(key)
        return value


def _cache_put(key: str, value: dict) -> None:
    with _PROFILE_CACHE_LOCK:
        _PROFILE_CACHE[key] = (time.time(), value)
        _PROFILE_CACHE.move_to_end(key)
        while len(_PROFILE_CACHE) > settings.PROFILE_CACHE_SIZE:
            _PROFILE_CACHE.popitem(last=False)


@traced("cv-extraction")
def extract_profile_from_cv(contents: bytes, filename: str) -> dict:
    """Extract a structured candidate profile from an in-memory CV.

    Fast path: reads the native PDF/DOCX/TXT text layer (pypdf/docx) — no OCR.
    Scanned/image-only PDFs (no text layer) fall back to a single batched
    vision-OCR call (deepseek-ocr). The structured profile is then parsed from
    the text with a small model; identical files (same SHA-256) are served
    from an in-memory cache — no model call. Returns
    {"text": full CV text, "profile": structured profile, "ocr": bool}.
    """
    cache_key = hashlib.sha256(contents).hexdigest()
    set_span_io(
        input={
            "filename": Path(filename).name,
            "bytes": len(contents),
            "sha256": cache_key,
        }
    )

    suffix = Path(filename).suffix.lower()
    ocr_used = False
    text = extract_text_from_cv_bytes(contents, filename)
    if suffix == ".pdf" and len(text) < 60:
        from app.services import ai_client

        try:
            text = ocr_text_from_pdf(contents)
            ocr_used = True
        except ai_client.AIUnavailable:
            text = ""
    if len(text) < 60:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not read any text from this CV. It may be a scanned or "
                "image-based PDF without a readable text layer. Please enter "
                "your details manually instead."
            ),
        )

    cached = _cache_get(cache_key)
    if cached is not None:
        set_span_io(
            output={
                "text_len": len(cached["text"]),
                "profile": cached["profile"],
                "ocr": cached["ocr"],
                "cached": True,
            }
        )
        return cached

    profile = extract_candidate_profile(text)
    result = {"text": text, "profile": profile, "ocr": ocr_used}
    _cache_put(cache_key, result)
    set_span_io(
        output={
            "text_len": len(text),
            "profile": profile,
            "ocr": ocr_used,
        }
    )
    return result


def warm_ocr_model() -> None:
    """Warm up the OCR vision model in a background thread at startup.

    The first invocation of a multi-GB model is a cold load that can take a
    minute; doing it once at startup (with keep_alive) makes the first real
    scanned-CV request fast.
    """
    try:
        import pymupdf

        doc = pymupdf.open()
        page = doc.new_page(width=200, height=100)
        page.insert_text((10, 50), "warmup", fontsize=14)
        pix = page.get_pixmap(dpi=72)
        png = base64.b64encode(pix.tobytes("png")).decode("ascii")
        doc.close()
        from app.services import ai_client

        ai_client.ocr_images([png], model=settings.OLLAMA_OCR_MODEL)
    except Exception:
        pass


def validate_cv(text: str, profile: dict) -> dict:
    issues = []
    if len(text) < 100:
        issues.append("CV appears to contain too little text to be meaningful")
    if not profile.get("email"):
        issues.append("No email address found in CV")
    if not profile.get("name"):
        issues.append("Could not extract a candidate name")
    if not profile.get("skills"):
        issues.append("No skills detected in CV")
    if not (profile.get("education") or profile.get("experience")):
        issues.append("No education or experience information found")

    return {
        "valid": len(issues) == 0,
        "requires_review": not (len(issues) == 0),
        "issues": issues,
    }


def detect_duplicates(db: Session, candidate: Candidate, cv: CVDocument) -> dict:
    reasons = []

    same_email = (
        db.query(Candidate)
        .filter(
            Candidate.email == candidate.email,
            Candidate.id != candidate.id,
            Candidate.deleted_at.is_(None),
        )
        .first()
    )
    if same_email:
        reasons.append(f"Another candidate already exists with this email ({candidate.email})")

    if cv.file_hash:
        dup_cv = (
            db.query(CVDocument)
            .filter(CVDocument.file_hash == cv.file_hash, CVDocument.id != cv.id)
            .first()
        )
        if dup_cv:
            reasons.append("An identical CV file has already been uploaded for another application")

    return {"is_duplicate": len(reasons) > 0, "reasons": reasons}


def should_embed_candidate(profile: dict) -> bool:
    return bool(profile.get("skills")) or bool(profile.get("experience"))


def build_embedding_source(profile: dict) -> str:
    parts = [profile.get("name") or ""]
    parts.extend(profile.get("skills") or [])
    parts.extend(profile.get("experience") or [])
    parts.extend(profile.get("education") or [])
    return "\n".join([str(p) for p in parts if p])


def update_job_requirements(job: Job) -> list[str]:
    reqs = job.requirements or {}
    out = []
    if isinstance(reqs, dict):
        for key in ("skills", "requirements", "must_have", "nice_to_have"):
            value = reqs.get(key)
            if isinstance(value, list):
                out.extend(str(v) for v in value)
            elif isinstance(value, str):
                out.append(value)
        for key in ("experience", "education"):
            value = reqs.get(key)
            if value:
                out.append(str(value))
    elif isinstance(reqs, list):
        out.extend(str(r) for r in reqs)
    return [r for r in out if r]