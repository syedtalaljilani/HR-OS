# HR Recruitment OS Evaluation

## 1. Purpose

The evaluation measures whether the HR Recruitment OS improves the recruitment workflow without removing human control.

The system is evaluated on:

```text
Screening quality
Requirement matching
Evidence accuracy
Unsupported claims
Uncertainty detection
Human override
Workflow reliability
Candidate tracking
Interview evaluation
Non-developer usability
```

The evaluation should compare the automated workflow against the existing manual process and a simple ChatGPT baseline.

---

# 2. Evaluation Approach

Three workflows are compared:

```text
Existing Manual Process
        ↓
Simple ChatGPT Baseline
        ↓
HR Recruitment OS
```

The same test cases should be used where possible.

The evaluation should use real or anonymized CVs and job descriptions. Sensitive candidate information should be removed or anonymized before testing.

---

# 3. Baseline

## Manual Baseline

Record the current recruitment workflow used by HR.

Measure:

```text
Candidate data entry effort
CV screening effort
Candidate tracking effort
Interview evaluation effort
Paper usage
Status tracking effort
Communication effort
```

Do not invent baseline numbers.

Actual measurements should be recorded during testing.

Example:

```text
Metric                         Manual
-----------------------------------------
Candidate data entry           TBD
CV screening time              TBD
Tracking effort                TBD
Paper interview forms          TBD
Communication effort           TBD
```

## Simple ChatGPT Baseline

Give the same job description and candidate CV to a general ChatGPT session.

Ask it to:

```text
Extract candidate information
Match candidate against requirements
Identify missing requirements
Provide evidence
Give a screening recommendation
```

Record:

```text
Recommendation
Evidence quality
Unsupported claims
Missing requirements
Uncertainty handling
Output consistency
```

This provides a simple AI baseline for comparison.

---

# 4. Screening Evaluation Rubric

Each candidate screening result is scored out of 100.

| Criterion                |  Weight |
| ------------------------ | ------: |
| Requirement Matching     |      25 |
| Evidence Accuracy        |      25 |
| Unsupported Claims       |      15 |
| Screening Recommendation |      15 |
| Consistency              |      10 |
| Next Action              |      10 |
| **Total**                | **100** |

## Requirement Matching

Evaluate whether mandatory and preferred requirements were correctly classified.

```text
25 = Accurate
20 = Minor issue
10 = Several issues
0 = Major failure
```

## Evidence Accuracy

Check whether claims are directly supported by the CV.

```text
25 = Evidence is accurate and traceable
20 = Minor evidence issue
10 = Several weak claims
0 = Evidence is fabricated or materially incorrect
```

## Unsupported Claims

The target is:

```text
0 unsupported claims
```

Any fabricated candidate information is considered a critical failure.

## Screening Recommendation

Check whether the final recommendation reflects the verified requirements.

Allowed recommendations:

```text
MATCH
PARTIAL
MISSING
UNCLEAR
```

The recommendation must not exceed the evidence available.

## Consistency

Run the same candidate multiple times when appropriate.

The workflow should produce materially consistent results.

## Next Action

The system should identify the correct next action.

Examples:

```text
Continue to HR review
Request verification
Escalate uncertainty
Check duplicate
Review salary mismatch
```

---

# 5. Test Cases

## TC01: Clear Match

### Input

Candidate clearly satisfies all mandatory requirements.

### Expected

```text
Recommendation: MATCH
Evidence: Present
HR escalation: No
```

### Purpose

Tests normal successful screening.

---

## TC02: Missing One Required Skill

### Input

Candidate satisfies most requirements but lacks one mandatory skill.

### Expected

```text
Recommendation: PARTIAL or MISSING
Missing requirement: Clearly identified
Evidence: Provided
```

### Purpose

Tests mandatory requirement handling.

---

## TC03: Insufficient Experience

### Input

Job requires more experience than the candidate has.

### Expected

```text
Recommendation: PARTIAL or MISSING
Experience mismatch: Identified
```

### Purpose

Tests experience comparison.

---

## TC04: Related but Different Technology

### Input

Candidate has experience with a related technology but not the exact required technology.

### Expected

```text
Recommendation: PARTIAL or UNCLEAR
Related experience: Identified
No false MATCH
```

### Purpose

Tests whether keyword similarity is incorrectly treated as direct experience.

---

## TC05: Insufficient Information

### Input

CV does not contain enough information to verify an important requirement.

### Expected

```text
Recommendation: UNCLEAR
Uncertainty: Identified
HR review: Required
```

### Purpose

Tests uncertainty handling.

---

## TC06: Keyword Without Evidence

### Input

A required skill appears in the CV but there is no evidence of actual experience.

### Expected

```text
No automatic assumption of expertise
Evidence quality: Low
HR review: Possible
```

### Purpose

Tests evidence-based screening.

---

## TC07: Strong Candidate Missing Mandatory Requirement

### Input

Candidate has strong experience but clearly fails one mandatory requirement.

### Expected

```text
Mandatory requirement: Clearly identified
Recommendation: Not MATCH
Reason: Evidence-based
```

### Purpose

Tests whether strong overall experience incorrectly overrides mandatory requirements.

---

## TC08: Inconsistent Employment Information

### Input

Employment dates or roles contain contradictions.

### Expected

```text
Uncertainty: Identified
Issue: Clearly described
HR review: Required
```

### Purpose

Tests validation and escalation.

---

## TC09: Duplicate CV

### Input

The same candidate submits the same or substantially identical CV more than once.

### Expected

```text
Possible duplicate: Detected
Candidate record: Not unnecessarily duplicated
HR review: Available
```

### Purpose

Tests duplicate detection and data integrity.

---

## TC10: Salary Outside Range

### Input

Candidate expected salary is outside the approved job range.

### Expected

```text
Salary mismatch: Identified
Screening decision: Not automatically rejected
HR review: Required
```

### Purpose

Tests separation between deterministic salary checks and hiring decisions.

---

# 6. HITL Evaluation

Human-in-the-loop controls are evaluated separately.

| Test   | Expected Behaviour                                               |
| ------ | ---------------------------------------------------------------- |
| HITL01 | HR can override incorrect AI recommendation                      |
| HITL02 | Unclear requirement is escalated                                 |
| HITL03 | Suspicious CV is flagged instead of declared fraudulent          |
| HITL04 | Salary mismatch goes to HR review                                |
| HITL05 | HR can override ranking                                          |
| HITL06 | HR can edit AI-generated feedback                                |
| HITL07 | Authorized users can correct interview scores with audit history |

## HITL Success Criteria

```text
Uncertainty detection       >= 90%
Correct escalation          >= 90%
Human override capability   100%
Critical AI decisions       Human controlled
Audit history               100% for overrides
```

---

# 7. Reliability Evaluation

The system should be tested beyond successful inputs.

## Failure Scenarios

```text
Invalid CV
Corrupted PDF
Empty CV
Unsupported file
LLM timeout
Ollama unavailable
Invalid LLM JSON
Database failure
Email failure
Duplicate application
Expired tracking token
Unauthorized request
Invalid status transition
```

## Expected Behaviour

The system should:

```text
Validate input
Retry recoverable failures
Log errors
Avoid silent failures
Preserve application data
Escalate unresolved AI failures
Prevent unauthorized access
```

---

# 8. Authentication and Authorization Tests

## Candidate

Test that candidates can:

```text
Submit application
Receive application ID
Access their secure tracking link
View allowed application status
View interview schedule
View final outcome
```

Candidates must not be able to access:

```text
AI ranking
AI score
HR notes
Interviewer comments
Interviewer scores
Internal validation flags
Other candidates
Audit logs
```

## HR

HR should be able to:

```text
Create jobs
Review applications
Review AI recommendations
Override recommendations
Manage interviews
Review scorecards
Manage Talent Pool
Make final decisions
Approve communications
```

## Interviewer

Interviewers should only access assigned interviews.

They should be able to:

```text
View assigned candidate information
View interview details
Submit scorecard
Update their own permitted scorecard data
```

They should not be able to:

```text
View unrelated candidates
Change final application status
Make final hiring decisions
Access HR-only notes
```

---

# 9. Talent Pool Evaluation

The Talent Pool is tested as a reusable recruitment workflow.

## Test

```text
Candidate
   ↓
HR adds candidate to Talent Pool
   ↓
New Job
   ↓
Semantic Retrieval
   ↓
AI Matching
   ↓
HR Review
   ↓
Candidate Contact
```

Expected:

```text
Relevant candidates are retrieved
Evidence is provided
Irrelevant candidates are not presented as strong matches
HR approval is required before contact
Candidate response is recorded
```

Test both:

```text
Interested
Not Interested
```

The candidate should remain in the Talent Pool when appropriate.

---

# 10. Interview Evaluation

Create one technical interview with four interviewers.

Each interviewer submits an independent scorecard.

Example:

```text
Interviewer 1 = 82
Interviewer 2 = 76
Interviewer 3 = 88
Interviewer 4 = 80
```

Expected combined score:

```text
(82 + 76 + 88 + 80) / 4 = 81.5
```

The backend calculates the combined score.

The AI does not modify individual interviewer scores.

---

# 11. Status Transition Evaluation

The application lifecycle should be tested:

```text
APPLIED
↓
PROCESSING
↓
HR_REVIEW
↓
SHORTLISTED
↓
INTERVIEW_SCHEDULED
↓
TECHNICAL_INTERVIEW
↓
TECHNICAL_REVIEW
↓
BEHAVIORAL_INTERVIEW
↓
FINAL_REVIEW
↓
SELECTED / HOLD / REJECTED
```

Every important status change should create a history record.

Example:

```text
from_status: HR_REVIEW
to_status: SHORTLISTED
changed_by: HR_USER_ID
reason: "Approved after CV review"
timestamp: ...
```

Invalid transitions should be rejected by the backend.

---

# 12. Email Evaluation

Test:

```text
Application confirmation
Interview invitation
Status update
Talent Pool contact
Selection email
Rejection email
```

For rejection:

```text
AI Draft
   ↓
HR Review
   ↓
HR Edit
   ↓
HR Approval
   ↓
Email
```

No rejection email should be sent before HR approval.

For selection:

```text
HR Final Decision
+
Joining Date
↓
Approval
↓
Congratulations Email
```

---

# 13. Regression Testing

Whenever a prompt, model, workflow or scoring rule changes, rerun the evaluation dataset.

Minimum regression set:

```text
TC01
TC02
TC03
TC04
TC05
TC06
TC07
TC08
TC09
TC10
```

Compare:

```text
Previous result
New result
Changed output
Reason for change
Pass / Fail
```

A model or prompt update should not be considered an improvement if it fixes one test while breaking previously passing critical cases.

---

# 14. Target Success Metrics

The following targets define the initial V1 success criteria.

| Metric                                   |    Target |
| ---------------------------------------- | --------: |
| Candidate data entry time reduction      |    >= 70% |
| CV screening time reduction              |    >= 50% |
| Screening quality                        | >= 85/100 |
| Requirement matching                     |    >= 90% |
| Evidence accuracy                        |    >= 95% |
| Unsupported claims                       |         0 |
| Paper-based interview forms              |         0 |
| Test cases passed                        |   >= 8/10 |
| HITL escalation accuracy                 |    >= 90% |
| Critical AI decisions with human control |      100% |

These are targets, not measured results.

Actual results must be recorded after testing.

---

# 15. Evaluation Results

Use the following table during Day 4 and Day 5.

| Test Case | Expected                 | Actual | Pass/Fail | Root Cause | Fix | Retest |
| --------- | ------------------------ | ------ | --------- | ---------- | --- | ------ |
| TC01      | Clear match              | TBD    | TBD       |            |     |        |
| TC02      | Missing skill            | TBD    | TBD       |            |     |        |
| TC03      | Experience mismatch      | TBD    | TBD       |            |     |        |
| TC04      | Related technology       | TBD    | TBD       |            |     |        |
| TC05      | Unclear information      | TBD    | TBD       |            |     |        |
| TC06      | Keyword without evidence | TBD    | TBD       |            |     |        |
| TC07      | Mandatory requirement    | TBD    | TBD       |            |     |        |
| TC08      | Inconsistent CV          | TBD    | TBD       |            |     |        |
| TC09      | Duplicate CV             | TBD    | TBD       |            |     |        |
| TC10      | Salary mismatch          | TBD    | TBD       |            |     |        |

---

# 16. Failure Analysis

At least three real failures should be documented during testing.

For each failure:

```text
Test Case:
Expected:
Actual:
Why it failed:
Root Cause:
Fix:
Retest Result:
```

Example structure:

```text
Test Case: TC04

Expected:
Related technology should not automatically receive MATCH.

Actual:
System classified candidate as MATCH.

Root Cause:
Matching prompt treated semantic similarity as direct requirement satisfaction.

Fix:
Added explicit evidence requirement and PARTIAL/UNCLEAR classification rule.

Retest:
PASS
```

The example above is only a documentation format. Actual failures should come from real system testing.

---

# 17. Non-Developer Usability Test

A non-developer HR user should be able to complete the core workflow without developer assistance.

Test:

```text
Login
↓
Create Job
↓
Publish Job
↓
Review Applications
↓
Review AI Screening
↓
Override Recommendation
↓
Shortlist Candidate
↓
Assign Interviewers
↓
Review Scorecards
↓
Make Final Decision
↓
Approve Candidate Communication
```

Record:

```text
Task
Completed?
Assistance Required?
Confusion Point
Time Taken
```

Success means the HR user can understand what action is required at each stage without needing to understand the underlying AI implementation.

---

# 18. Evaluation Completion Criteria

The evaluation package is complete when:

```text
10 screening test cases executed
At least 3 real failures documented
Failures have root-cause analysis
Fixes are implemented
Failed cases are retested
HITL controls tested
Authentication tested
Authorization tested
Talent Pool tested
Interview scoring tested
Email workflow tested
Regression suite executed
Final metrics recorded
Known limitations documented
```

The evaluation should report both successes and failures.

The goal is not to demonstrate that the AI is always correct.

The goal is to demonstrate that the system produces useful recommendations, detects uncertainty, fails safely, and keeps important decisions under human control.
