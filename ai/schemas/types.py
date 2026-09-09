"""Pydantic models for structured AI node outputs.

These mirror the JSON schemas defined in docs/architecture/prompt.md.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MatchStatus = Literal["MATCH", "PARTIAL", "MISSING", "UNCLEAR"]
Severity = Literal["LOW", "MEDIUM", "HIGH"]
UncertaintyLevel = Literal["LOW", "MEDIUM", "HIGH"]


def _entry_to_text(entry: dict) -> str:
    """Render a structured education/experience entry as a readable string."""
    if "degree" in entry:
        parts = [entry.get("degree")]
        if entry.get("field"):
            parts.append("in " + str(entry["field"]))
        if entry.get("institution"):
            parts.append("(" + str(entry["institution"]) + ")")
        return " ".join(p for p in parts if p)
    if "years" in entry:
        raw = str(entry.get("years", ""))
        text = raw
        if not text.endswith(("+", "years")):
            text += " years"
        if entry.get("type"):
            text += f" ({entry['type']})"
        return text
    if "title" in entry:
        parts = [str(entry.get("title"))]
        if entry.get("level"):
            parts.append(str(entry["level"]))
        return " ".join(p for p in parts if p)
    return str(entry)


# --- CV Extraction (prompt.md section 2) ---
class EducationEntry(BaseModel):
    degree: str
    field: str | None = None
    institution: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ExperienceEntry(BaseModel):
    company: str
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str = ""


class CandidateProfile(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


# --- CV Validation (prompt.md section 3) ---
class ValidationIssue(BaseModel):
    type: str
    description: str
    severity: Severity = "MEDIUM"


class CVValidation(BaseModel):
    valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    requires_hr_review: bool = False


# --- Job Requirement Extraction (prompt.md section 4) ---
class SalaryRange(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str | None = None


class JobRequirements(BaseModel):
    mandatory: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    technical_skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    location: list[str] = Field(default_factory=list)
    salary: SalaryRange = Field(default_factory=SalaryRange)

    @field_validator("education", "experience", mode="before")
    @classmethod
    def _flatten_entries(cls, value):
        """Models sometimes return structured entries instead of strings."""
        if not isinstance(value, list):
            return value
        out: list[str] = []
        for entry in value:
            if isinstance(entry, str):
                out.append(entry)
            elif isinstance(entry, dict):
                out.append(_entry_to_text(entry))
        return out

    @model_validator(mode="after")
    def _dedupe(self):
        """Deduplicate requirements across overlapping fields (case-insensitive).

        LLMs often repeat the same requirement in multiple fields (e.g.
        mandatory + technical_skills + certifications). Duplicates inflate the
        matching denominator and distort the final score, so keep only the
        first occurrence in field order.
        """
        seen: set[str] = set()

        def clean(items: list[str]) -> list[str]:
            out: list[str] = []
            for item in items:
                key = item.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    out.append(item.strip())
            return out

        for field in (
            "mandatory",
            "preferred",
            "technical_skills",
            "education",
            "experience",
            "certifications",
            "location",
        ):
            setattr(self, field, clean(getattr(self, field)))
        return self

    def as_flat_list(self) -> list[str]:
        out: list[str] = []
        out.extend(self.mandatory)
        out.extend(self.preferred)
        out.extend(self.technical_skills)
        out.extend(self.education)
        out.extend(self.experience)
        out.extend(self.certifications)
        out.extend(self.location)
        return [r for r in out if r]


# --- Requirement Matching (prompt.md section 5) ---
class MatchedRequirement(BaseModel):
    requirement: str
    status: MatchStatus
    evidence: str | None = None
    is_mandatory: bool = False


# --- Evidence Verification (prompt.md section 6) ---
class EvidenceItem(BaseModel):
    claim: str
    supported: bool = True
    evidence: str | None = None
    reason: str = ""


# --- Uncertainty Detection (prompt.md section 7) ---
class UncertaintyItem(BaseModel):
    issue: str
    impact: Severity = "MEDIUM"
    requires_hr_review: bool = True


class UncertaintyResult(BaseModel):
    uncertainties: list[UncertaintyItem] = Field(default_factory=list)
    overall_uncertainty: UncertaintyLevel = "LOW"


# --- Screening Recommendation (prompt.md section 8) ---
class ScreeningRecommendation(BaseModel):
    recommendation: MatchStatus
    score: int = Field(default=0, ge=0, le=100)
    reason: str = ""
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    requires_hr_review: bool = False
