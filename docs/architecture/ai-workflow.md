# HR Recruitment OS AI Workflow

## AI Stack

| Component              | Technology            |
| ---------------------- | --------------------- |
| Workflow Orchestration | LangGraph             |
| LLM Runtime            | Ollama                |
| LLM                    | Qwen                  |
| Embeddings             | Embedding Model       |
| Vector Search          | PostgreSQL + pgvector |

## Recruitment AI Flow

```text
CV Upload
   ↓
CV Extraction
   ↓
CV Validation
   ↓
Duplicate Check
   ↓
Requirement Matching
   ↓
Evidence Extraction
   ↓
Uncertainty Check
   ↓
Screening Recommendation
   ↓
HR Review
```

## LangGraph State

The LangGraph workflow maintains a shared state throughout the screening process.

```text
RecruitmentState

application_id
job_id
cv_text
candidate_data
job_requirements
validation_result
duplicate_result
matched_requirements
missing_requirements
evidence
uncertainties
recommendation
score
errors
```

## Node 1: CV Extraction

Input:

```text
CV Document
```

Process:

```text
PDF/DOCX
   ↓
Text Extraction
   ↓
Structured Candidate Data
```

Output:

```json
{
  "name": "Candidate Name",
  "email": "candidate@example.com",
  "education": [],
  "experience": [],
  "skills": []
}
```

The extracted information is stored in PostgreSQL.

## Node 2: CV Validation

Checks:

```text
Missing information
Unreadable content
Incomplete CV
Inconsistent information
Irrelevant application
Suspicious information
```

Output:

```json
{
  "valid": true,
  "issues": [],
  "uncertainty": []
}
```

If important information cannot be verified, the workflow flags the application for HR review.

The system does not automatically label a candidate as fraudulent.

## Node 3: Duplicate Check

Duplicate detection is primarily deterministic.

Checks can include:

```text
Email
Phone
CV hash
Existing candidate record
```

If a possible duplicate is detected:

```text
Duplicate
   ↓
HR Review
```

## Node 4: Requirement Matching

The job requirements are compared with the candidate profile.

Each requirement receives a status:

```text
MATCH
PARTIAL
MISSING
UNCLEAR
```

Example:

```json
{
  "requirement": "3 years Python experience",
  "status": "MATCH",
  "evidence": "4 years of Python development experience"
}
```

The system should provide evidence instead of relying only on keyword matches.

## Node 5: Evidence Extraction

For every important recommendation, the workflow identifies supporting information from the CV.

```text
Requirement
    ↓
Candidate Evidence
    ↓
Match Status
```

Unsupported claims should not be generated.

## Node 6: Uncertainty Check

The workflow identifies information that cannot be confidently verified.

Examples:

```text
Missing employment dates
Unclear degree information
Ambiguous years of experience
Conflicting CV information
```

Output:

```json
{
  "requires_hr_review": true,
  "uncertainties": [
    "Employment dates for previous role are unclear"
  ]
}
```

## Node 7: Screening Recommendation

The workflow generates an AI recommendation.

Allowed outputs:

```text
MATCH
PARTIAL
MISSING
UNCLEAR
```

Example:

```json
{
  "recommendation": "MATCH",
  "score": 87,
  "evidence": [],
  "missing_requirements": [],
  "uncertainty": [],
  "requires_hr_review": false
}
```

The recommendation is stored in `screening_results`.

## Human Review

```text
AI Recommendation
       ↓
    HR Review
       ↓
 ┌─────┴─────┐
 ↓           ↓
Accept     Override
 ↓           ↓
Continue   HR Decision
```

AI cannot directly:

```text
SELECTED
REJECTED
```

## Talent Pool AI Workflow

```text
New Job
   ↓
Job Requirements
   ↓
Embedding
   ↓
pgvector Search
   ↓
Relevant Candidates
   ↓
LangGraph Matching
   ↓
Evidence + Recommendation
   ↓
HR Review
   ↓
Contact Candidate
```

pgvector is used for candidate retrieval.

LangGraph performs the deeper requirement matching after retrieval.

## Interview AI

AI is not responsible for interviewer scoring.

Interviewers submit their own scores.

```text
Interviewer 1 → Scorecard
Interviewer 2 → Scorecard
Interviewer 3 → Scorecard
Interviewer 4 → Scorecard
                     ↓
              Backend Calculation
                     ↓
              Combined Score
```

The individual scores and comments remain unchanged.

## Feedback Drafting

For rejected candidates:

```text
Interview / Screening Data
          ↓
     LangGraph
          ↓
   Feedback Draft
          ↓
       HR Review
          ↓
     HR Approval
          ↓
    Candidate Email
```

AI only drafts the feedback.

HR approves the final message.

## Error Handling

If an AI node fails:

```text
AI Error
   ↓
Retry
   ↓
Still Failed?
   ↓
Flag Application
   ↓
HR Review
```

The system should not silently create a recommendation when required AI processing has failed.

## AI Responsibility Boundary

```text
LangGraph + Ollama

✓ CV understanding
✓ Information extraction
✓ Requirement matching
✓ Evidence identification
✓ Uncertainty detection
✓ Screening recommendation
✓ Talent Pool matching
✓ Feedback drafting


Backend

✓ Authentication
✓ Authorization
✓ Database
✓ Application IDs
✓ Status transitions
✓ Duplicate checks
✓ Salary comparison
✓ Interview score calculation
✓ Audit logs
✓ Email triggers


HR

✓ Review
✓ Override
✓ Shortlist
✓ Interview evaluation
✓ Final hiring decision
```

## Core Principle

```text
AI recommends
      ↓
Human verifies
      ↓
Human evaluates
      ↓
HR decides
      ↓
System communicates
```
