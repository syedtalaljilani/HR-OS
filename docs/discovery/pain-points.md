# Recruitment Pain Points

## Priority Problems

| Problem              | Current Situation                                    | Impact                         |
| -------------------- | ---------------------------------------------------- | ------------------------------ |
| Candidate data entry | CV information manually entered into Excel           | Repetitive work                |
| CV screening         | HR manually reads CVs                                | High manual effort             |
| Candidate tracking   | Excel used for multiple tracking activities          | Difficult to maintain          |
| Call tracking        | Candidate responses recorded manually                | Coordination effort            |
| Interview attendance | Attendance tracked manually                          | Additional administrative work |
| Interview evaluation | Department feedback recorded on paper                | Paper dependency               |
| HR evaluation        | HR feedback recorded on paper                        | Paper dependency               |
| Candidate comparison | Information reviewed manually                        | Time consuming                 |
| Communication        | Candidate communication requires manual coordination | Additional HR effort           |

## Core Bottlenecks

### 1. Manual CV Data Entry

HR has to open CVs, extract relevant information and enter it into Excel.

### 2. Manual Screening

HR spends time reviewing CVs individually to determine candidate suitability.

### 3. Fragmented Tracking

Candidate information, call responses and attendance depend on Excel based tracking.

### 4. Paper Based Interviews

Interview feedback is collected on paper instead of being stored as structured digital data.

### 5. Manual Candidate Comparison

HR has to manually bring together candidate information and interview feedback before making a decision.

## What Should Improve

```text
Manual CV Reading
        ↓
Structured CV Extraction

Manual Data Entry
        ↓
Automatic Candidate Record

Manual Screening
        ↓
AI Assisted Screening

Excel Tracking
        ↓
Central Application Tracking

Paper Evaluation
        ↓
Digital Scorecards

Manual Comparison
        ↓
Structured Candidate Comparison
```

## Reliability Requirement

Automation should not remove HR control.

When information is missing, unclear or inconsistent, the system should flag it for HR review instead of making an unsupported assumption.

## Measurement

The following metrics will be measured during testing:

| Metric                              |  Target |
| ----------------------------------- | ------: |
| Candidate data entry time reduction |    ≥70% |
| CV screening time reduction         |    ≥50% |
| Screening quality                   | ≥85/100 |
| Requirement matching                |    ≥90% |
| Evidence accuracy                   |    ≥95% |
| Unsupported claims                  |       0 |
| Paper based interview forms         |       0 |
| Test cases passed                   |   ≥8/10 |
| HITL escalation accuracy            |    ≥90% |
