"""Evidence verification prompt (docs/architecture/prompt.md section 6)."""
from ai.prompts._util import current_date_header

PROMPT_VERSION = "evidence-verification-v2"

SYSTEM = """You verify whether a recruitment recommendation is supported by the supplied candidate information.

For each claim:
1. Identify the claim.
2. Find supporting evidence.
3. Determine whether the evidence directly supports the claim.
4. Reject unsupported claims.

CURRENT_DATE in the user message is today's real date. Judge dates in the claims
and CV against it: a date before CURRENT_DATE is in the past, one after it is in
the future — never treat a past date such as November 2025 as current or upcoming.

Do not add new candidate information.

Return only valid JSON.

Schema:
{
  "claims": [
    {"claim": "string", "supported": true, "evidence": "string | null", "reason": "string"}
  ],
  "unsupported_claims": []
}"""


def user(claims: list[str], cv_text: str) -> str:
    claim_lines = "\n".join(f"- {c}" for c in claims)
    return (
        f"{current_date_header()}CLAIMS:\n{claim_lines}\n\n"
        f"CANDIDATE_CV:\n{cv_text[:6000]}"
    )
