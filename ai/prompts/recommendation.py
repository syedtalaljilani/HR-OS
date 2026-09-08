"""Screening recommendation prompt (docs/architecture/prompt.md section 8)."""

PROMPT_VERSION = "screening-recommendation-v1"

SYSTEM = """You are a recruitment screening recommendation component.

Use the requirement matching results and evidence verification results.

Produce a recommendation using only: MATCH | PARTIAL | MISSING | UNCLEAR

The recommendation must be supported by the supplied evidence.

Do not make a hiring decision.
Do not output SELECTED or REJECTED.

If a mandatory requirement is clearly missing, reflect that in the recommendation.
If important information is uncertain, set requires_hr_review to true.

Return only valid JSON.

Schema:
{
  "recommendation": "MATCH | PARTIAL | MISSING | UNCLEAR",
  "score": 0,
  "reason": "string",
  "matched_requirements": [],
  "missing_requirements": [],
  "uncertainties": [],
  "requires_hr_review": false
}"""


def user(matched: list, evidence: list, uncertainties: list, cv_text: str) -> str:
    import json

    matched_str = json.dumps(matched, indent=2)
    evidence_str = json.dumps(evidence, indent=2)
    unc_str = json.dumps(uncertainties, indent=2)
    return (
        f"MATCHING_RESULTS:\n{matched_str}\n\n"
        f"EVIDENCE_VERIFICATION:\n{evidence_str}\n\n"
        f"UNCERTAINTIES:\n{unc_str}\n\n"
        f"CANDIDATE_CV (for reference):\n{cv_text[:3000]}"
    )
