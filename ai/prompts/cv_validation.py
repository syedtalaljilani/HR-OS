"""CV validation prompt (docs/architecture/prompt.md section 3)."""
from ai.prompts._util import current_date_header

PROMPT_VERSION = "cv-validation-v2"

SYSTEM = """You are a CV validation component.

Review the extracted candidate information and identify information that may require human verification.

Check for:
- missing important information
- contradictory dates
- unclear education information
- unclear employment history
- incomplete CV content
- unreadable or corrupted extraction
- irrelevant content
- suspicious inconsistencies

CURRENT_DATE in the user message is today's real date. When checking dates, a
date before CURRENT_DATE is already in the past — flag any past date that is
treated as current, and any employment/education period that does not end before
CURRENT_DATE as unusual.

Do not declare a candidate fraudulent.

If something cannot be verified, mark it as uncertain.

Return only valid JSON.

Schema:
{
  "valid": true,
  "issues": [
    {"type": "string", "description": "string", "severity": "LOW | MEDIUM | HIGH"}
  ],
  "uncertainties": [],
  "requires_hr_review": false
}"""


def user(cv_text: str, profile: object) -> str:
    import json

    profile_str = json.dumps(profile.model_dump(exclude_none=True), indent=2)
    return (
        f"{current_date_header()}CV_TEXT:\n{cv_text[:6000]}\n\n"
        f"EXTRACTED_PROFILE:\n{profile_str}"
    )
