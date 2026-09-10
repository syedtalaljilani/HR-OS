"""Deterministic (non-LLM) judges.

These score signals that can be measured exactly from the data already recorded
in a trace: degenerate OCR output, screening rule adherence, placeholder
leakage in emails, job-title coverage, and CV profile shape sanity. They are
fast, free, and regression-safe — no ground truth needed.
"""
import re
from collections import Counter
from typing import Any

_SCORE_ITEMS = {"MATCH": 100, "PARTIAL": 50, "UNCLEAR": 25, "MISSING": 0}
_MANDATORY_WEIGHT = 2.0

_PROFILE_SCALAR_KEYS = ("name", "email", "phone", "address", "expected_salary", "summary")
_PROFILE_LIST_KEYS = ("skills", "languages", "interests", "links")
_PROFILE_OBJECT_KEYS = (
    "education",
    "experience",
    "projects",
    "certifications",
    "publications",
)


def ocr_text_quality(text: str) -> tuple[float, list[str]]:
    """Score OCR text quality, flagging degenerate/hallucinated repetition.

    The failure seen in production was the model echoing its system prompt
    thousands of times. Two signals catch that class reliably: line-level
    duplicates and identical 64-char windows.
    """
    if not text:
        return 0.0, ["empty OCR output"]
    sample = text[:40000]
    duplicates_fraction = 0.0

    lines = [ln.strip() for ln in sample.splitlines() if ln.strip()]
    if lines:
        counts = Counter(lines)
        dup = sum(c for c in counts.values() if c > 1) - sum(
            1 for c in counts.values() if c > 1
        )
        duplicates_fraction = max(duplicates_fraction, dup / len(lines))

    window = 64
    if len(sample) > window * 2:
        seen: set[str] = set()
        dup_windows = 0
        for i in range(len(sample) - window):
            chunk = sample[i : i + window]
            if chunk in seen:
                dup_windows += 1
            else:
                seen.add(chunk)
        duplicates_fraction = max(duplicates_fraction, dup_windows / (len(sample) - window))

    quality = max(0.0, 1.0 - duplicates_fraction)
    issues: list[str] = []
    if quality < 0.9:
        issues.append(
            f"heavy repetition: {duplicates_fraction:.0%} of the output repeats itself"
        )
    return round(min(quality, 1.0), 3), issues


def _expect_score_change(matched: list[dict]) -> int:
    """Re-implementation of ai.nodes.recommendation._compute_score."""
    if not matched:
        return 0
    total_weight = 0.0
    total = 0.0
    for m in matched:
        weight = _MANDATORY_WEIGHT if m.get("is_mandatory") else 1.0
        total_weight += weight
        total += _SCORE_ITEMS.get(str(m.get("status", "")).upper(), 0) * weight
    if total_weight == 0:
        return 0
    score = total / total_weight
    cap = None
    for m in matched:
        if not m.get("is_mandatory"):
            continue
        status = str(m.get("status", "")).upper()
        if status == "MISSING":
            cap = min(cap or 35, 35)
        elif status == "UNCLEAR":
            cap = min(cap or 55, 55)
        elif status == "PARTIAL":
            cap = min(cap or 80, 80)
    if cap is not None:
        score = min(score, cap)
    return int(score)


def screening_rules(
    matched: list[dict] | None, recommendation: dict | None
) -> tuple[float, list[str]]:
    """Verify the deterministic screening rules held up for this run."""
    issues: list[str] = []
    matched = matched if isinstance(matched, list) else []
    recommendation = recommendation if isinstance(recommendation, dict) else {}

    uncertain = [
        m.get("requirement")
        for m in matched
        if str(m.get("status", "")).upper() == "UNCLEAR"
    ]
    if uncertain and not recommendation.get("requires_hr_review"):
        issues.append(
            "uncertain requirement(s) present but requires_hr_review is False"
        )

    score = recommendation.get("score")
    if score is not None:
        expected = _expect_score_change(matched)
        try:
            if abs(int(float(score)) - expected) > 1:
                issues.append(f"score {score} disagrees with recomputed {expected}")
        except (TypeError, ValueError):
            issues.append(f"score is not numeric: {score!r}")

    rec = str(recommendation.get("recommendation", "")).upper()
    if rec and score is not None:
        if float(score) >= 70 and rec != "MATCH":
            issues.append(f"score>=70 but recommendation is {rec}")
        elif 40 <= float(score) < 70 and rec not in ("PARTIAL", "MATCH"):
            issues.append(f"40<=score<70 but recommendation is {rec}")

    return (0.0 if issues else 1.0, issues)


def email_placeholders(subject: str | None, body: str | None) -> tuple[float, list[str]]:
    """Flag leftover template placeholders like {HR_NAME} or [COMPANY_NAME]."""
    text = f"{subject or ''}\n{body or ''}"
    found = re.findall(r"[\[\{][A-Z][A-Z0-9 _\-]{0,40}[\]\}]", text)
    issues = [f"unresolved placeholder: {p}" for p in found[:5]] if found else []
    return (0.0 if found else 1.0, issues)


def email_shape(subject: str | None, body: str | None) -> tuple[float, list[str]]:
    issues: list[str] = []
    if not subject:
        issues.append("missing subject")
    elif len(subject) > 150:
        issues.append("subject is overly long")
    if not body:
        issues.append("empty email body")
    elif len(body) < 40:
        issues.append("email body too short to be a real draft")
    return (0.0 if issues else 1.0, issues)


def job_title_coverage(title: str | None, description: str | None) -> tuple[float, list[str]]:
    if not title:
        return 0.0, ["no job title available to check"]
    if not description:
        return 0.0, ["empty job description"]
    ok = title.strip().lower() in description.lower()
    return (1.0 if ok else 0.0, [] if ok else ["job title not mentioned in draft"])


def job_draft_shape(description: str | None) -> tuple[float, list[str]]:
    if not description:
        return 0.0, ["empty job description"]
    issues: list[str] = []
    if len(description) < 200:
        issues.append("draft too short to be a useful job description")
    if "Responsibilities".lower() not in description.lower() and len(description.split()) < 60:
        issues.append("draft may lack section structure")
    return (0.0 if issues else 1.0, issues)


def extraction_shape(profile: dict | None) -> tuple[float, list[str]]:
    """Check the extracted profile honours the documented JSON contract."""
    if not isinstance(profile, dict):
        return 0.0, ["profile output is not an object"]
    issues: list[str] = []
    checks = 0
    for key in _PROFILE_SCALAR_KEYS:
        checks += 1
        if key not in profile:
            issues.append(f"missing scalar key: {key}")
    for key in _PROFILE_LIST_KEYS:
        checks += 1
        if key not in profile:
            issues.append(f"missing list key: {key}")
        elif not isinstance(profile[key], list):
            issues.append(f"{key} is not a list")
    for key in _PROFILE_OBJECT_KEYS:
        checks += 1
        if key not in profile:
            issues.append(f"missing object key: {key}")
        elif not isinstance(profile[key], list):
            issues.append(f"{key} is not a list")
        else:
            non_dict = [i for i in profile[key] if not isinstance(i, dict)]
            if non_dict:
                issues.append(f"{key} contains non-object entries")
    core = [
        bool(profile.get("name")),
        bool(profile.get("email")),
        bool(profile.get("skills")),
        bool(profile.get("education") or profile.get("experience")),
    ]
    checks += 1
    if not any(core):
        issues.append("profile has no name/email/skills/experience at all")
    score = max(0.0, 1.0 - len(issues) / checks) if checks else 0.0
    return round(score, 3), issues