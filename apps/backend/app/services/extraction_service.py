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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text: {e}",
        )
    raise HTTPException(status_code=400, detail="Unsupported CV file type")


def extract_text_from_cv_bytes(contents: bytes, filename: str) -> str:
    """Extract the embedded text layer from an in-memory CV (PDF/DOCX/TXT)."""
    suffix = Path(filename).suffix.lower()
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
    raise HTTPException(status_code=400, detail="Unsupported CV file type")


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


def extract_profile_from_cv(contents: bytes, filename: str) -> dict:
    """Extract the full native text layer from a CV and structure it.

    No OCR — reads the embedded PDF/DOCX/TXT text layer (pypdf/docx), then
    parses it into a structured profile with a small model. Identical files
    (same SHA-256) are served from an in-memory cache — no model call.
    Returns {"text": full CV text, "profile": structured profile}.
    """
    cache_key = hashlib.sha256(contents).hexdigest()
    text = extract_text_from_cv_bytes(contents, filename)
    if len(text) < 60:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not read any text from this CV. It may be a scanned or "
                "image-based PDF without a text layer. Please enter your details "
                "manually instead."
            ),
        )

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    profile = extract_candidate_profile(text)
    result = {"text": text, "profile": profile}
    _cache_put(cache_key, result)
    return result


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