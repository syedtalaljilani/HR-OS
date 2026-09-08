# Recruitment OS V1 Scope

## V1 Objective

Build a paperless recruitment workflow that reduces repetitive HR work while keeping HR in control of screening, interviews and final hiring decisions.

## Core Workflow

```text
Create Job
    ↓
Generate / Improve JD
    ↓
HR Approves JD
    ↓
Publish Job
    ↓
Candidate Applies
    ↓
CV Upload
    ↓
Application ID + Secure Tracking Link
    ↓
CV Processing
    ↓
CV Validation
    ↓
AI Screening
    ↓
HR Review
    ↓
HR Approve / Override
    ↓
Shortlist
    ↓
Interview Scheduled
    ↓
Technical Interview
    ↓
Digital Scorecard
    ↓
HR Interview
    ↓
Digital Scorecard
    ↓
Combined Interview Score
    ↓
Final HR Review
    ↓
Selected / Hold / Rejected
```

## V1 Features

### Job Management

HR can:

* Create jobs
* Define requirements
* Generate or improve job descriptions
* Review and approve job descriptions
* Publish jobs

### Candidate Application

Candidates can apply without creating an account.

Application form:

```text
Full Name
Email
Phone
CV / Resume
Expected Salary
Consent
```

The system generates:

```text
Application ID
Secure Tracking Token
```

Example:

```text
APP-2026-00421
```

### CV Processing

The system extracts relevant information from uploaded CVs.

It should identify:

* Education
* Experience
* Skills
* Previous employment
* Contact information
* Other job relevant information

### CV Validation

The system checks for:

* Missing information
* Unreadable CV
* Duplicate CV
* Incomplete information
* Inconsistent information
* Irrelevant application
* Unclear or suspicious information

Uncertain cases are flagged for HR review.

The system should not automatically declare a CV fraudulent.

### AI Screening

LangGraph manages the screening workflow.

Ollama provides the local LLM.

The system evaluates candidates against job requirements and provides:

```text
Match
Partial Match
Missing
Unclear
```

Each recommendation should include supporting evidence from the CV.

### HR Review

HR can:

* Review AI recommendation
* Accept recommendation
* Override recommendation
* Shortlist candidate
* Move candidate to another status

AI cannot make the final hiring decision.

### Talent Pool

Suitable candidates can be retained for future opportunities.

```text
Candidate
    ↓
HR Adds to Talent Pool
    ↓
New Job
    ↓
AI Matching
    ↓
HR Review
    ↓
Contact Candidate
    ↓
Interested?
   ↙   ↘
 YES    NO
  ↓      ↓
Pipeline  Talent Pool
```

### Interview Management

HR can:

* Schedule interviews
* Assign interviewers
* Track interview status
* Collect digital scorecards
* View combined scores

Multiple interviewers can independently evaluate the same candidate.

### Final Decision

HR makes the final decision:

```text
SELECTED
HOLD
REJECTED
```

For selected candidates, HR confirms the joining date before the system sends the congratulations email.

For rejected candidates, the system can draft job related feedback, but HR must review and approve it before sending.

## Human In The Loop

```text
AI
↓
Recommendation
↓
HR Review
↓
HR Override if Required
↓
Final HR Decision
```

Critical decisions remain under HR control.

## Candidate Visibility

Candidates can see:

* Application status
* Interview schedule
* Final outcome

Candidates cannot see:

* AI ranking
* Internal scores
* HR notes
* Interviewer comments
* Internal validation flags
* Internal audit information

## Non Goals

V1 will not include:

* Payroll
* Employee management
* Attendance management
* Full HR ERP
* Background checks
* LinkedIn scraping
* Automated hiring decisions
* Automatic rejection without HR approval
* Personality inference
* Sensitive attribute inference
* Facial analysis
* Voice analysis
* Full onboarding

## V1 Success Criteria

The system should demonstrate:

```text
✓ Candidate can apply
✓ CV can be processed
✓ Candidate data is structured
✓ AI screening works
✓ HR can review and override
✓ Candidate status is tracked
✓ Interviews can be scheduled
✓ Multiple interviewers can score
✓ Scores are combined deterministically
✓ Talent Pool works
✓ Candidate communication works
✓ HR makes final decision
✓ Audit history is maintained
```
