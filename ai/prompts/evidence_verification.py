"""Evidence verification prompt (docs/architecture/prompt.md section 6)."""

PROMPT_VERSION = "evidence-verification-v1"

SYSTEM = """You verify whether a recruitment recommendation is supported by the supplied candidate information.

For each claim:
1. Identify the claim.
2. Find supporting evidence.
3. Determine whether the evidence directly supports the claim.
4. Reject unsupported claims.

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
    return f"CLAIMS:\n{claim_lines}\n\nCANDIDATE_CV:\n{cv_text[:6000]}"
