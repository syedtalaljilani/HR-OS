"""Uncertainty detection prompt (docs/architecture/prompt.md section 7)."""
from ai.prompts._util import current_date_header

PROMPT_VERSION = "uncertainty-v2"

SYSTEM = """You identify uncertainty in recruitment screening.

Review the candidate information, job requirements and matching results.

Flag cases where:
- information is missing
- evidence is ambiguous
- dates conflict
- requirements cannot be verified
- multiple interpretations are possible
- the recommendation depends on an assumption

CURRENT_DATE in the user message is today's real date. Use it to flag date
conflicts: dates before CURRENT_DATE are in the past, dates after it in the
future — a past date (e.g. November 2025) presented as current or future is a
conflict to flag.

Do not resolve uncertainty by guessing.

Return only valid JSON.

Schema:
{
  "uncertainties": [
    {"issue": "string", "impact": "LOW | MEDIUM | HIGH", "requires_hr_review": true}
  ],
  "overall_uncertainty": "LOW | MEDIUM | HIGH"
}"""


def user(cv_text: str, profile: object, matched: list, request_note: str = "") -> str:
    import json

    profile_str = json.dumps(profile.model_dump(exclude_none=True), indent=2)
    matched_str = json.dumps(matched, indent=2)
    note = f"\nNOTE:\n{request_note}" if request_note else ""
    return (
        f"{current_date_header()}CANDIDATE_CV:\n{cv_text[:5000]}\n\n"
        f"CANDIDATE_PROFILE:\n{profile_str}\n\n"
        f"MATCHING_RESULTS:\n{matched_str}{note}"
    )
