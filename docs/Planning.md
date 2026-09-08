# HR Recruitment OS

## 5-Day Build Sprint Plan

**Duration:** 5 Days
**Working Time:** ~8 hours/day
**Goal:** Build and validate a working HR Recruitment OS for Evyol Group of Industries.

---

# 1. Project Goal

The goal is to bring the main recruitment process into one system.

The system will cover:

```text
Job Creation
    ↓
Job Publishing
    ↓
Candidate Application
    ↓
CV Processing
    ↓
Candidate Screening
    ↓
HR Review
    ↓
Shortlisting / Talent Pool
    ↓
Interview Scheduling
    ↓
Technical Evaluation
    ↓
HR Evaluation
    ↓
Final HR Decision
    ↓
Candidate Communication
```

The system should reduce repetitive HR work while keeping important decisions with HR.

---

# 2. Current Problem

The current recruitment workflow uses several manual steps.

```text
CVs Received
    ↓
Open CV
    ↓
Read CV
    ↓
Enter Data in Excel
    ↓
Screen Candidate
    ↓
Call Candidate
    ↓
Track Call / Response
    ↓
Track Attendance
    ↓
Department Interview
    ↓
Paper Feedback
    ↓
HR Interview
    ↓
Paper Feedback
    ↓
Compare Candidates
    ↓
Final Decision
```

Main problems:

* Candidate information is manually entered into Excel.
* CVs have to be reviewed individually.
* Candidate communication is tracked manually.
* Interview attendance is tracked manually.
* Interview feedback is paper-based.
* Candidate information is spread across different places.
* It is difficult to reuse suitable candidates for future jobs.
* There is no single application history for each candidate.

---

# 3. Target Users

## HR

Main system user.

HR can:

* Create jobs
* Publish jobs
* Review candidates
* Review screening results
* Override recommendations
* Shortlist candidates
* Manage Talent Pool
* Schedule interviews
* Assign interviewers
* Review interview scores
* Make final decisions
* Send candidate communications

## Candidate

Candidate can:

* View job
* Apply
* Upload CV
* Receive confirmation
* Track application
* Receive interview updates
* Receive final decision

Candidate does not need an account.

## Interviewer

Interviewer can:

* Log in
* View assigned interviews
* View assigned candidates
* Complete scorecards
* Add interview feedback

Interviewer cannot make the final hiring decision.

## Admin

Admin can:

* Manage users
* Manage HR accounts
* Manage interviewer accounts
* Manage settings
* View audit logs

---

# 4. Project Scope

## Included in V1

### Job Management

* Create job
* Edit job
* Job requirements
* Job description
* HR approval
* Publish job

### Candidate Management

* Public application
* CV upload
* Application ID
* Secure tracking link
* Candidate status
* Application history

### CV Processing

* PDF/DOCX processing
* Text extraction
* CV data extraction
* Validation
* Duplicate detection
* Missing information detection

### Screening

* Requirement matching
* Evidence extraction
* Candidate ranking
* HR review
* HR override

### Talent Pool

* Add candidates
* Search candidates
* Match candidates against future jobs
* Contact candidates
* Track response
* Move interested candidates into active recruitment

### Interviews

* Schedule interviews
* Assign interviewers
* Technical scorecard
* HR scorecard
* Multiple interviewer evaluation
* Combined score

### Final Decision

* Selected
* Hold
* Rejected
* Joining date
* Candidate communication

### Administration

* Authentication
* RBAC
* Audit logs

---

# 5. Non-Goals

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
* Sensitive-attribute inference
* Facial analysis
* Voice analysis
* Full onboarding

---

# 6. Overall System Workflow

```text
                         JOB
                          ↓
                       PUBLISH
                          ↓
                     APPLICATION
                          ↓
                       CV UPLOAD
                          ↓
                    APPLICATION ID
                          ↓
                     CV PROCESSING
                          ↓
                     CV VALIDATION
                          ↓
                  REQUIREMENT MATCH
                          ↓
                       HR REVIEW
                    /            \
                   /              \
             SHORTLIST         TALENT POOL
                 ↓                  ↓
             INTERVIEW          FUTURE JOB
                 ↓                  ↓
           INTERVIEWERS         MATCHING
                 ↓                  ↓
             SCORECARDS         HR REVIEW
                 ↓                  ↓
          COMBINED SCORE      CONTACT CANDIDATE
                 ↓                  ↓
              HR REVIEW        INTERESTED?
                 ↓              /        \
          FINAL DECISION      YES         NO
             /   |   \         ↓           ↓
        SELECT HOLD REJECT  PIPELINE    REMAIN
             ↓      ↓          ↓        IN POOL
           EMAIL  EMAIL     INTERVIEW
```

---

# DAY 1 — DISCOVER, MAP & PLAN

## Objective

Understand the existing recruitment workflow, define V1, decide what will be measured, and prepare the system design for implementation.

---

## 7. Day 1 — Current Workflow

Document the actual HR process:

```text
Job Opening
    ↓
CVs Received
    ↓
Open CV
    ↓
Read CV
    ↓
Manual Excel Data Entry
    ↓
Candidate Screening
    ↓
Interview Call
    ↓
Call / Response Tracking
    ↓
Attendance Tracking
    ↓
Department Interview
    ↓
Paper Evaluation
    ↓
HR Interview
    ↓
Paper Evaluation
    ↓
Candidate Comparison
    ↓
Final HR Decision
    ↓
Candidate Communication
```

---

## 8. Day 1 — Problem Definition

Document:

* Where HR spends most manual effort
* Which information is entered manually
* Where information gets duplicated
* Where candidate tracking becomes difficult
* Where interview evaluation is difficult
* Where delays happen
* Which steps can be standardized

Do not invent time or candidate-volume numbers.

Actual measurements will be collected during testing.

---

## 9. Day 1 — Baseline

Measure a small manual sample.

For example:

```text
Candidate 1
Candidate 2
Candidate 3
...
```

Record:

* CV data-entry time
* CV screening time
* Interview tracking effort
* Manual evaluation effort
* Candidate status tracking effort

The baseline will be used later to compare the new system.

---

# 10. Day 1 — Simple ChatGPT Baseline

Before building the full workflow, test a simple CV-screening approach.

Use:

```text
Job Description
+
Candidate CV
```

Ask for:

* Matching requirements
* Missing requirements
* Evidence
* Unclear information
* Recommendation

Record the result.

This provides a simple baseline against which the structured workflow can be compared.

---

# 11. Day 1 — V1 Requirements

### Must Have

* Job creation
* Public application
* CV upload
* Application ID
* Tracking link
* CV processing
* CV validation
* Requirement matching
* HR review
* Talent Pool
* Interview scheduling
* Interviewer assignment
* Technical scorecard
* HR scorecard
* Combined score
* Candidate status history
* Email notifications
* Authentication
* RBAC

### Should Have

* Duplicate detection
* OCR for scanned CVs
* Search
* Audit logs
* Retry handling
* Error handling

### Later

* Advanced analytics
* More HR workflows
* Advanced integrations
* Employee onboarding
* Full HR ERP features

---

# 12. Day 1 — Candidate Workflow

```text
Candidate
    ↓
Job Page
    ↓
Application Form
    ↓
CV Upload
    ↓
Application Created
    ↓
Application ID
    ↓
Secure Tracking Token
    ↓
Confirmation Email
```

---

# 13. Day 1 — Candidate Status

Candidate-facing:

```text
Application Received
↓
Under Review
↓
Shortlisted
↓
Interview Scheduled
↓
Technical Interview
↓
HR Interview
↓
Final Review
↓
Selected / Not Selected
```

Internal:

```text
APPLIED
PROCESSING
HR_REVIEW
SHORTLISTED
INTERVIEW_SCHEDULED
TECHNICAL_INTERVIEW
TECHNICAL_REVIEW
BEHAVIORAL_INTERVIEW
FINAL_REVIEW
SELECTED
HOLD
REJECTED
```

---

# 14. Day 1 — Talent Pool

Talent Pool is part of V1.

Workflow:

```text
Candidate
    ↓
Screening
    ↓
HR Review
    ↓
Talent Pool
    ↓
Future Job
    ↓
Candidate Matching
    ↓
HR Review
    ↓
Contact Candidate
    ↓
Candidate Response
```

Statuses:

```text
ACTIVE
CONTACTED
INTERESTED
NOT_INTERESTED
MOVED_TO_PIPELINE
EXPIRED
REMOVED
```

---

# 15. Day 1 — Interview Workflow

```text
Shortlisted
    ↓
Schedule Interview
    ↓
Assign Interviewers
    ↓
Interview
    ↓
Independent Scorecards
    ↓
Combined Score
    ↓
HR Review
```

Technical score:

```text
Technical Knowledge       /25
Problem Solving           /20
Practical Experience      /20
Role-Specific Skills      /20
Technical Communication   /15
                         ----
                         /100
```

HR score:

```text
Communication             /20
Teamwork                  /20
Leadership                /20
Adaptability              /15
Professionalism           /15
Role Fit                  /10
                         ----
                         /100
```

---

# 16. Day 1 — Test Cases

```text
TC01  Clear match
TC02  Missing required skill
TC03  Less experience
TC04  Related technology
TC05  Insufficient CV information
TC06  Keyword without evidence
TC07  Missing mandatory requirement
TC08  Inconsistent employment information
TC09  Duplicate CV
TC10  Salary outside range
```

Human review tests:

```text
HITL01  Wrong match → HR override
HITL02  Unclear requirement → HR review
HITL03  Suspicious CV → Flag for review
HITL04  Salary mismatch → HR decision
HITL05  Incorrect ranking → HR override
HITL06  Incorrect feedback → HR edit
HITL07  Score correction → Authorized correction + history
```

---

# 17. Day 1 — Evaluation Rubric

| Area                     |  Weight |
| ------------------------ | ------: |
| Requirement Matching     |      25 |
| Evidence Accuracy        |      25 |
| Unsupported Claims       |      15 |
| Screening Recommendation |      15 |
| Consistency              |      10 |
| Next Action              |      10 |
| **Total**                | **100** |

HITL evaluation:

* Uncertainty detection
* Correct escalation
* HR override
* Auditability
* Decision control

---

# 18. Day 1 — Success Metrics

Initial targets:

| Metric                              |  Target |
| ----------------------------------- | ------: |
| Candidate data-entry time reduction |    ≥70% |
| CV screening time reduction         |    ≥50% |
| Screening quality                   | ≥85/100 |
| Requirement matching                |    ≥90% |
| Evidence accuracy                   |    ≥95% |
| Unsupported claims                  |       0 |
| Paper interview forms               |       0 |
| Test cases passed                   |   ≥8/10 |
| HITL escalation accuracy            |    ≥90% |
| Critical AI decisions overridable   |    100% |

---

# 19. Day 1 Deliverables

* Current workflow
* Problem statement
* Baseline plan
* V1 scope
* Candidate flow
* Talent Pool flow
* Interview flow
* Roles and permissions
* Test cases
* Evaluation rubric
* Success metrics
* Security requirements
* Initial architecture

---

# DAY 2 — ARCHITECTURE + V0

## Objective

Turn the Day 1 plan into a technical design and build the first working version.

---

# 20. Day 2 — Architecture

Define:

* Frontend
* Backend
* Database
* File storage
* AI processing
* Email service
* Authentication
* Authorization
* Logging
* Audit history

Basic structure:

```text
Candidate Portal
       ↓
Backend API
       ↓
Database
       ↓
File Storage

Backend
   ├── CV Processing
   ├── Validation
   ├── Matching
   ├── Ranking
   ├── Talent Pool
   ├── Interviews
   ├── Email
   └── Audit Logs

HR Dashboard
       ↓
Backend API

Interviewer Dashboard
       ↓
Backend API
```

---

# 21. Day 2 — AI Components

Use separate components for specific tasks:

```text
Job Agent
CV Processing
CV Validation
Matching
Ranking
Feedback Drafting
```

These components should not control:

* Authentication
* Authorization
* Final decisions
* Interview score calculation
* Candidate permissions
* Audit history

---

# 22. Day 2 — Database

Initial entities:

```text
users
jobs
applications
candidates
candidate_documents
candidate_profiles
screening_results
talent_pool
interviews
interview_assignments
interview_scorecards
application_status_history
email_logs
audit_logs
tracking_tokens
```

---

# 23. Day 2 — Authentication

### Candidate

No account.

Uses:

```text
Application ID
+
Secure Token
```

### HR

Uses:

```text
Email
Password
Session/JWT
Role
```

### Interviewer

Uses a separate account and assignment-based access.

Roles:

```text
ADMIN
HR
INTERVIEWER
```

---

# 24. Day 2 — Candidate Tracking Security

Tracking token requirements:

* Cryptographically random
* Hashed in database
* Expirable
* Revocable
* Rate limited
* HTTPS only

Public URLs should not expose internal database IDs.

---

# 25. Day 2 — V0

Build one complete path:

```text
Create Job
    ↓
Publish Job
    ↓
Candidate Applies
    ↓
CV Upload
    ↓
Application Created
    ↓
CV Processing
    ↓
Screening
    ↓
HR Review
```

Use one real CV for the first end-to-end test.

---

# 26. Day 2 — Candidate Application

Build:

* Job page
* Application form
* CV upload
* Validation
* Application ID generation
* Tracking token
* Confirmation email

Example:

```text
APP-2026-00421
```

---

# 27. Day 2 — HR Dashboard

Initial dashboard should show:

* Jobs
* Applications
* Candidate details
* CV
* Screening result
* Matching evidence
* Status
* HR review
* Override action

---

# 28. Day 2 — Talent Pool

Implement:

```text
Add Candidate
View Candidate
Search Candidate
Filter Candidate
Match Candidate Against Job
Contact Candidate
Update Response
Move To Pipeline
```

---

# 29. Day 2 — Interview Design

Define:

```text
interviews
interview_assignments
interview_scorecards
```

Interviewer access should come from assignment.

---

# 30. Day 2 Deliverables

* Architecture diagram
* Database schema
* API plan
* Authentication design
* RBAC design
* Security design
* V0 candidate flow
* HR dashboard
* Candidate tracking
* Talent Pool structure
* Interview structure

---

# DAY 3 — BUILD & INTEGRATE

## Objective

Build the complete V1 workflow and connect the major components.

---

# 31. Day 3 — Main Build

Build:

```text
Job Management
       ↓
Candidate Application
       ↓
CV Processing
       ↓
Screening
       ↓
HR Review
       ↓
Talent Pool
       ↓
Interview Management
       ↓
Scorecards
       ↓
Final Decision
       ↓
Candidate Communication
```

---

# 32. Day 3 — Candidate Portal

Candidate should be able to:

1. Open job
2. Submit application
3. Upload CV
4. Receive application ID
5. Receive tracking link
6. Open status page
7. See application status
8. See interview schedule
9. See final outcome

---

# 33. Day 3 — HR Dashboard

HR should be able to:

* Create job
* Publish job
* View applications
* Open CV
* Review extracted data
* Review screening
* Override screening
* Shortlist
* Add to Talent Pool
* Schedule interviews
* Assign interviewers
* Review scorecards
* Make final decision
* Send candidate communication

---

# 34. Day 3 — Interviewer Dashboard

Interviewer should see:

```text
My Interviews
    ↓
Assigned Candidate
    ↓
Interview Details
    ↓
Scorecard
    ↓
Submit
```

They should not see unrelated candidates.

---

# 35. Day 3 — Multiple Interviewers

Example:

```text
Technical Interview
        ↓
 ┌──────┼──────┬──────┐
 ↓      ↓      ↓      ↓
I1     I2     I3     I4
 ↓      ↓      ↓      ↓
82     76     88     80
 └──────┼──────┬──────┘
        ↓
Combined Score
        ↓
HR Review
```

All individual scores remain stored.

---

# 36. Day 3 — Email Integration

Emails:

```text
Application Confirmation
        ↓
Interview Invitation
        ↓
Interview Reminder
        ↓
Status Update
        ↓
Selection Email
        ↓
Rejection / Feedback Email
```

Rejected candidate feedback must be reviewed by HR before sending.

---

# 37. Day 3 — Integrations

At least two external integrations should be working.

Possible integrations:

* Email provider
* File storage
* LLM/API
* OCR service
* Authentication provider

---

# 38. Day 3 — Error Handling

Handle:

* Invalid CV
* Empty CV
* Unsupported file
* Large file
* Failed CV processing
* Failed email
* Duplicate submission
* Expired token
* Unauthorized request
* API failure

---

# 39. Day 3 Definition of Done

```text
[ ] Candidate can apply
[ ] CV upload works
[ ] Application ID generated
[ ] Tracking link generated
[ ] CV processing works
[ ] Screening works
[ ] HR can review
[ ] HR can override
[ ] Talent Pool works
[ ] Future-job matching works
[ ] Interview can be scheduled
[ ] Interviewers can be assigned
[ ] Four interviewers can score
[ ] Combined score works
[ ] Status history works
[ ] Emails work
[ ] Authentication works
[ ] RBAC works
[ ] Two integrations work
[ ] Basic error handling works
```

---

# DAY 4 — TEST & IMPROVE

## Objective

Test the complete system, identify real failures, fix them, and retest.

---

# 40. Day 4 — End-to-End Testing

Run:

```text
Candidate Application
    ↓
CV Upload
    ↓
Processing
    ↓
Screening
    ↓
HR Review
    ↓
Shortlisting
    ↓
Interview
    ↓
Scorecards
    ↓
HR Decision
    ↓
Candidate Email
```

Test from both:

* Candidate side
* HR side

---

# 41. Day 4 — Functional Testing

Test:

* Job creation
* Job publishing
* Application
* CV upload
* CV extraction
* CV validation
* Screening
* Ranking
* HR override
* Talent Pool
* Future-job matching
* Interview scheduling
* Interview assignments
* Scorecards
* Combined score
* Status changes
* Emails

---

# 42. Day 4 — Permission Testing

### Candidate

Cannot:

* Access HR dashboard
* Access another candidate
* View internal notes
* View interviewer scores
* View internal ranking

### Interviewer

Cannot:

* Access unrelated candidates
* Change another interviewer's score
* Make final decisions

### HR

Can:

* Review
* Override
* Shortlist
* Manage Talent Pool
* Manage interviews
* Make final decisions

---

# 43. Day 4 — Error Testing

Test:

```text
Invalid CV
Large CV
Empty CV
Unsupported file
Unreadable CV
Duplicate CV
Missing email
Invalid token
Expired token
Unauthorized access
Duplicate interview assignment
Email failure
Processing failure
Database failure
```

---

# 44. Day 4 — Screening Testing

Run TC01–TC10.

Record:

| ID   | Expected | Actual | Pass/Fail |
| ---- | -------- | ------ | --------- |
| TC01 |          |        |           |
| TC02 |          |        |           |
| TC03 |          |        |           |
| TC04 |          |        |           |
| TC05 |          |        |           |
| TC06 |          |        |           |
| TC07 |          |        |           |
| TC08 |          |        |           |
| TC09 |          |        |           |
| TC10 |          |        |           |

---

# 45. Day 4 — Human Review Testing

Run HITL01–HITL07.

Check:

* HR can override
* Unclear cases are escalated
* Suspicious cases are flagged
* HR controls final decision
* Corrections are recorded
* Feedback can be edited
* Score corrections are auditable

---

# 46. Day 4 — Talent Pool Testing

Test:

```text
Candidate
    ↓
Add to Talent Pool
    ↓
Create Future Job
    ↓
Search Pool
    ↓
Match Candidates
    ↓
HR Review
    ↓
Contact Candidate
```

Then test:

```text
Interested → Move to Pipeline
Not Interested → Remain in Pool
Removed → No longer available
Expired → Expired status
```

---

# 47. Day 4 — Failure Analysis

At least three real failures should be documented.

For each:

```text
Problem
↓
Expected
↓
Actual
↓
Root Cause
↓
Fix
↓
Retest
↓
Result
```

Do not create fake failures for the report. Use actual problems found during testing.

---

# 48. Day 4 — Reliability

Check:

* Validation
* Retry behavior
* Fallback
* Duplicate detection
* Logging
* Audit history
* Permission enforcement
* HR override
* Uncertainty handling
* Regression

---

# 49. Day 4 — Regression

After fixes, rerun:

```text
Candidate Application
CV Processing
Screening
HR Dashboard
Talent Pool
Interview Assignment
Scorecards
Combined Score
Status Tracking
Emails
Candidate Tracking
Authentication
RBAC
```

---

# 50. Day 4 — Results

Record:

| Metric             | Result |
| ------------------ | -----: |
| Test Cases         |        |
| Passed             |        |
| Failed             |        |
| HITL Tests Passed  |        |
| Matching Accuracy  |        |
| Evidence Accuracy  |        |
| Unsupported Claims |        |
| Permission Tests   |        |
| Email Tests        |        |
| Regression Tests   |        |

---

# 51. Day 4 Deliverables

```text
[ ] TC01–TC10 completed
[ ] HITL tests completed
[ ] Talent Pool tested
[ ] Candidate tracking tested
[ ] Authentication tested
[ ] RBAC tested
[ ] Interview assignments tested
[ ] Multiple scoring tested
[ ] Email workflow tested
[ ] Error handling tested
[ ] 3+ real failures documented
[ ] Root causes identified
[ ] Fixes implemented
[ ] Failed cases retested
[ ] Regression completed
[ ] Final results recorded
```

---

# DAY 5 — SHIP, DOCUMENT & DEMO

## Objective

Prepare the system for someone else to use, document the results, and demonstrate the complete workflow.

---

# 52. Day 5 — Final System Check

Run the complete workflow one more time:

```text
Create Job
    ↓
Publish
    ↓
Apply
    ↓
CV Upload
    ↓
Processing
    ↓
Screening
    ↓
HR Review
    ↓
Talent Pool / Shortlist
    ↓
Interview
    ↓
Scorecards
    ↓
Final Decision
    ↓
Candidate Email
```

Fix any blocking issues before the final demo.

---

# 53. Day 5 — Documentation

Create:

```text
README.md
SETUP.md
ARCHITECTURE.md
API.md
EVALUATION.md
TEST_RESULTS.md
LIMITATIONS.md
```

README should explain:

* What the system does
* Who uses it
* Main workflow
* How to run it
* Main features

---

# 54. Day 5 — Setup Guide

Document:

```text
Requirements
    ↓
Environment Variables
    ↓
Database Setup
    ↓
Storage Setup
    ↓
Email Setup
    ↓
AI/API Keys
    ↓
Run Backend
    ↓
Run Frontend
    ↓
Create Admin
```

A non-developer should be able to follow the guide.

---

# 55. Day 5 — User Guide

Create short instructions for:

### HR

* Create job
* Publish job
* Review applications
* Review screening
* Shortlist
* Use Talent Pool
* Schedule interview
* Review scorecards
* Make final decision

### Interviewer

* Login
* Open assigned interview
* Review candidate
* Complete scorecard
* Submit feedback

### Candidate

* Apply
* Upload CV
* Open tracking link
* Check status
* View interview details

---

# 56. Day 5 — Evaluation Report

Include:

### Baseline

Manual process results.

### System Results

Time and quality measurements after using the system.

### Screening Evaluation

* Requirement matching
* Evidence accuracy
* Unsupported claims
* Recommendations
* Consistency

### HITL Evaluation

* Escalation
* Override
* Auditability
* Final decision control

### Reliability

* Test pass rate
* Error handling
* Duplicate handling
* Permission testing
* Regression testing

---

# 57. Day 5 — Case Study

Structure:

```text
Problem
↓
Current Workflow
↓
Pain Points
↓
What Was Built
↓
Architecture
↓
Implementation
↓
Testing
↓
Failures
↓
Fixes
↓
Results
↓
Limitations
↓
Next Steps
```

Use actual numbers from the sprint.

Do not claim improvements that were not measured.

---

# 58. Day 5 — Demo Flow

The demo should show one candidate from beginning to end.

### Part 1 — HR Creates Job

```text
HR Login
↓
Create Job
↓
Add Requirements
↓
Approve
↓
Publish
```

### Part 2 — Candidate Applies

```text
Open Job
↓
Application Form
↓
Upload CV
↓
Submit
↓
Application ID
↓
Tracking Link
↓
Confirmation Email
```

### Part 3 — Screening

```text
CV Processing
↓
Validation
↓
Requirement Matching
↓
HR Review
```

### Part 4 — HR Decision

```text
Review
↓
Override if Needed
↓
Shortlist
```

### Part 5 — Interview

```text
Schedule
↓
Assign 4 Interviewers
↓
Independent Scorecards
↓
Combined Score
```

### Part 6 — Final Decision

```text
HR Review
↓
Selected / Hold / Rejected
↓
Candidate Email
```

### Part 7 — Talent Pool

```text
Candidate
↓
Talent Pool
↓
New Job
↓
Matching
↓
HR Review
↓
Contact
↓
Interested
↓
Recruitment Pipeline
```

---

# 59. Day 5 — Final Deliverables

## Working System

```text
[ ] Candidate Portal
[ ] HR Dashboard
[ ] Interviewer Dashboard
[ ] Job Management
[ ] CV Processing
[ ] Screening
[ ] Talent Pool
[ ] Interview Management
[ ] Scorecards
[ ] Candidate Tracking
[ ] Email Notifications
[ ] Authentication
[ ] RBAC
[ ] Audit History
```

## Documentation

```text
[ ] README
[ ] Setup Guide
[ ] Architecture
[ ] API Documentation
[ ] User Guide
[ ] Evaluation
[ ] Test Results
[ ] Limitations
```

## Presentation

```text
[ ] Demo Video
[ ] Case Study
[ ] Results
[ ] Failure Analysis
[ ] Future Plan
```

---

# 60. Final 5-Day Schedule

| Day   | Hours | Focus                | Output                                         |
| ----- | ----: | -------------------- | ---------------------------------------------- |
| Day 1 |   ~8h | Discover, Map & Plan | Requirements, workflow, scope, metrics         |
| Day 2 |   ~8h | Architecture + V0    | Architecture, schema, APIs, first working flow |
| Day 3 |   ~8h | Build & Integrate    | Complete working V1                            |
| Day 4 |   ~8h | Test & Improve       | Test results, failures, fixes                  |
| Day 5 |   ~8h | Ship & Handoff       | Documentation, case study, demo                |

---

# 61. Final Architecture

```text
                         ┌───────────────┐
                         │   Candidate   │
                         └───────┬───────┘
                                 │
                                 ▼
                       ┌─────────────────┐
                       │ Public Job Page │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Application API │
                       └────────┬────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
       ┌────────────┐    ┌────────────┐    ┌────────────┐
       │ File Store │    │  Database  │    │Email Service│
       └─────┬──────┘    └──────┬─────┘    └────────────┘
             │                  │
             ▼                  │
       ┌─────────────┐          │
       │ CV Process  │          │
       └──────┬──────┘          │
              ▼                 │
       ┌─────────────┐          │
       │ CV Validate │          │
       └──────┬──────┘          │
              ▼                 │
       ┌─────────────┐          │
       │   Matching  │          │
       └──────┬──────┘          │
              ▼                 │
       ┌─────────────┐          │
       │   Ranking   │          │
       └──────┬──────┘          │
              │                 │
              └────────┬────────┘
                       ▼
                ┌──────────────┐
                │ HR Dashboard │
                └──────┬───────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
     Talent Pool   Interviews    HR Review
                       │            │
                       ▼            │
                Interviewers       │
                       │            │
                       ▼            │
                  Scorecards        │
                       │            │
                       └─────┬──────┘
                             ▼
                       Final HR Decision
                             │
                             ▼
                    Candidate Communication
```

---

# 62. Responsibility Split

The system should keep responsibilities clear.

| Area                 | System | AI               | HR                     |
| -------------------- | ------ | ---------------- | ---------------------- |
| Application ID       | ✓      |                  |                        |
| CV Storage           | ✓      |                  |                        |
| CV Extraction        |        | ✓                | Review                 |
| CV Validation        |        | ✓                | Review                 |
| Requirement Matching |        | ✓                | Review                 |
| Ranking              |        | ✓                | Override               |
| Talent Pool          | ✓      | Matching support | ✓                      |
| Interview Scheduling | ✓      |                  | ✓                      |
| Interview Assignment | ✓      |                  | ✓                      |
| Interview Score      | ✓      |                  | ✓                      |
| Combined Score       | ✓      |                  | Review                 |
| Final Decision       |        |                  | ✓                      |
| Candidate Email      | ✓      | Draft support    | Approve where required |
| Audit History        | ✓      |                  |                        |
| Authentication       | ✓      |                  |                        |
| Authorization        | ✓      |                  |                        |

---

# 63. Important Rules

1. HR controls the final hiring decision.
2. AI results must be reviewable.
3. HR must be able to override recommendations.
4. Unclear information should be marked as unclear.
5. Suspicious CVs should be flagged for review rather than automatically declared fraudulent.
6. Candidate-facing pages must not expose internal HR information.
7. Interviewers only access assigned interviews.
8. Individual interviewer scores remain separate.
9. Talent Pool candidates must have appropriate consent and retention handling.
10. Every important status change should have a history.
11. Automated communication should not bypass required HR approval.
12. Measurements must come from actual testing.

---

# 64. Final Success Criteria

The sprint is successful if the final system can demonstrate:

```text
HR creates a job
        ↓
Candidate applies
        ↓
CV is processed
        ↓
Candidate is screened
        ↓
HR reviews and can override
        ↓
Candidate is shortlisted or added to Talent Pool
        ↓
Interview is scheduled
        ↓
Multiple interviewers independently evaluate
        ↓
Scores are combined
        ↓
HR makes final decision
        ↓
Candidate receives appropriate communication
```

And the system has:

* Working candidate portal
* Working HR dashboard
* Working interviewer dashboard
* Working Talent Pool
* Working candidate tracking
* Working interview scorecards
* Working authentication and permissions
* Tested error handling
* Measured evaluation results
* Documented failures and fixes
* Setup instructions
* Final demo

---

# 65. Final Project Outcome

At the end of the 5-day sprint, the deliverable is not just a CV screening tool.

It is a working recruitment workflow covering:

```text
JOB
 ↓
APPLICATION
 ↓
CV
 ↓
SCREENING
 ↓
HR REVIEW
 ↓
TALENT POOL / SHORTLIST
 ↓
INTERVIEW
 ↓
EVALUATION
 ↓
FINAL DECISION
 ↓
COMMUNICATION
```

The system should be usable by HR without requiring the developer to manually operate every recruitment step.
