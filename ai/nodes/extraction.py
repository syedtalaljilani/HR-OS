"""Node 1: CV Extraction."""
import re

from ai.prompts import cv_extraction
from ai.schemas import CandidateProfile, EducationEntry
from ai.schemas.state import ScreeningState

from ._util import NodeError, llm_json

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "sql", "postgresql",
    "mongodb", "redis", "fastapi", "django", "flask", "react", "nextjs", "node",
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "pandas", "numpy",
    "machine learning", "deep learning", "llm", "nlp", "devops", "ci/cd",
    "microservices", "rest api", "graphql", "html", "css", "tailwind",
]

EDUCATION_KEYWORDS = (
    "bachelor", "master", "phd", "bs ", "ms ", "b.s.", "m.s.",
    "degree", "university", "college",
)


def _fallback(text: str) -> CandidateProfile:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email = next(
        (
            m.group(0)
            for ln in lines
            for m in [re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", ln)]
            if m
        ),
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

    low = text.lower()
    skills = [s for s in SKILL_KEYWORDS if s in low]

    education: list[EducationEntry] = []
    seen: list[str] = []
    for keyword in EDUCATION_KEYWORDS:
        if keyword in low and keyword not in seen:
            seen.append(keyword)
            education.append(EducationEntry(degree=keyword.strip().title()))
        if len(education) >= 5:
            break

    return CandidateProfile(
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        education=education,
    )


def run(state: ScreeningState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions)
    model = state.model

    try:
        raw, prompt_versions, model = llm_json(
            cv_extraction.SYSTEM,
            cv_extraction.user(state.cv_text),
            prompt_version=cv_extraction.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        profile = CandidateProfile.model_validate(raw)
    except (NodeError, ValueError):
        errors.append("cv_extraction: LLM failed, used deterministic fallback")
        profile = _fallback(state.cv_text)

    return {
        "candidate_profile": profile,
        "errors": errors,
        "prompt_versions": prompt_versions,
        "model": model,
    }