# HR Recruitment OS Database Schema

## users

| Field         | Type      | Description            |
| ------------- | --------- | ---------------------- |
| id            | UUID      | Primary key            |
| name          | VARCHAR   | User name              |
| email         | VARCHAR   | Unique email           |
| password_hash | VARCHAR   | Hashed password        |
| role          | ENUM      | ADMIN, HR, INTERVIEWER |
| is_active     | BOOLEAN   | Account status         |
| created_at    | TIMESTAMP | Created time           |
| updated_at    | TIMESTAMP | Updated time           |

## jobs

| Field        | Type      | Description                                          |
| ------------ | --------- | ---------------------------------------------------- |
| id           | UUID      | Primary key                                          |
| title        | VARCHAR   | Job title                                            |
| description  | TEXT      | Job description                                      |
| requirements | JSONB     | Skills, education, experience and other requirements |
| location     | VARCHAR   | Job location                                         |
| salary_min   | DECIMAL   | Minimum salary                                       |
| salary_max   | DECIMAL   | Maximum salary                                       |
| status       | ENUM      | DRAFT, OPEN, CLOSED                                  |
| created_by   | UUID      | HR user                                              |
| created_at   | TIMESTAMP | Created time                                         |
| updated_at   | TIMESTAMP | Updated time                                         |

## candidates

| Field        | Type      | Description                      |
| ------------ | --------- | -------------------------------- |
| id           | UUID      | Primary key                      |
| full_name    | VARCHAR   | Candidate name                   |
| email        | VARCHAR   | Candidate email                  |
| phone        | VARCHAR   | Candidate phone                  |
| address      | TEXT      | Candidate address                |
| profile_data | JSONB     | Structured CV information        |
| embedding    | VECTOR    | Candidate embedding for pgvector |
| created_at   | TIMESTAMP | Created time                     |
| updated_at   | TIMESTAMP | Updated time                     |

## applications

| Field           | Type      | Description                                                                                                                                                           |
| --------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id              | UUID      | Primary key                                                                                                                                                           |
| application_id  | VARCHAR   | Public ID e.g. APP-2026-00421                                                                                                                                         |
| candidate_id    | UUID      | Candidate                                                                                                                                                             |
| job_id          | UUID      | Job                                                                                                                                                                   |
| expected_salary | DECIMAL   | Expected salary                                                                                                                                                       |
| status          | ENUM      | APPLIED, PROCESSING, HR_REVIEW, SHORTLISTED, INTERVIEW_SCHEDULED, TECHNICAL_INTERVIEW, TECHNICAL_REVIEW, BEHAVIORAL_INTERVIEW, FINAL_REVIEW, SELECTED, HOLD, REJECTED |
| consent         | BOOLEAN   | Application consent                                                                                                                                                   |
| created_at      | TIMESTAMP | Application time                                                                                                                                                      |
| updated_at      | TIMESTAMP | Updated time                                                                                                                                                          |

## application_tracking_tokens

| Field          | Type      | Description         |
| -------------- | --------- | ------------------- |
| id             | UUID      | Primary key         |
| application_id | UUID      | Application         |
| token_hash     | VARCHAR   | Hashed secure token |
| expires_at     | TIMESTAMP | Token expiry        |
| revoked_at     | TIMESTAMP | Token revocation    |
| created_at     | TIMESTAMP | Created time        |

## cv_documents

| Field             | Type      | Description                |
| ----------------- | --------- | -------------------------- |
| id                | UUID      | Primary key                |
| application_id    | UUID      | Application                |
| file_name         | VARCHAR   | Original file name         |
| file_path         | VARCHAR   | Storage path               |
| mime_type         | VARCHAR   | File type                  |
| extracted_text    | TEXT      | Extracted CV text          |
| extraction_status | ENUM      | PENDING, COMPLETED, FAILED |
| created_at        | TIMESTAMP | Upload time                |

## screening_results

| Field                | Type      | Description                      |
| -------------------- | --------- | -------------------------------- |
| id                   | UUID      | Primary key                      |
| application_id       | UUID      | Application                      |
| recommendation       | ENUM      | MATCH, PARTIAL, MISSING, UNCLEAR |
| score                | DECIMAL   | Screening score                  |
| evidence             | JSONB     | Evidence from CV                 |
| missing_requirements | JSONB     | Missing requirements             |
| uncertainty          | JSONB     | Uncertain information            |
| model                | VARCHAR   | Ollama model used                |
| hr_decision          | ENUM      | PENDING, ACCEPTED, OVERRIDDEN    |
| reviewed_by          | UUID      | HR reviewer                      |
| created_at           | TIMESTAMP | Screening time                   |

## application_status_history

| Field          | Type      | Description     |
| -------------- | --------- | --------------- |
| id             | UUID      | Primary key     |
| application_id | UUID      | Application     |
| from_status    | VARCHAR   | Previous status |
| to_status      | VARCHAR   | New status      |
| changed_by     | UUID      | User            |
| reason         | TEXT      | Reason          |
| created_at     | TIMESTAMP | Change time     |

## talent_pool

| Field                 | Type      | Description                                                                        |
| --------------------- | --------- | ---------------------------------------------------------------------------------- |
| id                    | UUID      | Primary key                                                                        |
| candidate_id          | UUID      | Candidate                                                                          |
| source_application_id | UUID      | Original application                                                               |
| status                | ENUM      | ACTIVE, CONTACTED, INTERESTED, NOT_INTERESTED, MOVED_TO_PIPELINE, EXPIRED, REMOVED |
| consent               | BOOLEAN   | Talent Pool consent                                                                |
| added_by              | UUID      | HR user                                                                            |
| created_at            | TIMESTAMP | Added time                                                                         |
| updated_at            | TIMESTAMP | Updated time                                                                       |

## interviews

| Field          | Type      | Description                     |
| -------------- | --------- | ------------------------------- |
| id             | UUID      | Primary key                     |
| application_id | UUID      | Application                     |
| type           | ENUM      | TECHNICAL, HR                   |
| scheduled_at   | TIMESTAMP | Interview time                  |
| status         | ENUM      | SCHEDULED, COMPLETED, CANCELLED |
| created_by     | UUID      | HR user                         |
| created_at     | TIMESTAMP | Created time                    |

## interview_assignments

| Field          | Type      | Description          |
| -------------- | --------- | -------------------- |
| id             | UUID      | Primary key          |
| interview_id   | UUID      | Interview            |
| interviewer_id | UUID      | Assigned interviewer |
| assigned_by    | UUID      | HR/Admin             |
| status         | ENUM      | ASSIGNED, COMPLETED  |
| assigned_at    | TIMESTAMP | Assignment time      |

## interview_scorecards

| Field          | Type      | Description                |
| -------------- | --------- | -------------------------- |
| id             | UUID      | Primary key                |
| interview_id   | UUID      | Interview                  |
| interviewer_id | UUID      | Interviewer                |
| scores         | JSONB     | Individual category scores |
| total_score    | DECIMAL   | Score out of 100           |
| comments       | TEXT      | Interview feedback         |
| submitted_at   | TIMESTAMP | Submission time            |
| updated_at     | TIMESTAMP | Updated time               |

## interview_combined_scores

| Field             | Type      | Description                    |
| ----------------- | --------- | ------------------------------ |
| id                | UUID      | Primary key                    |
| interview_id      | UUID      | Interview                      |
| combined_score    | DECIMAL   | Average of individual scores   |
| interviewer_count | INTEGER   | Number of submitted scorecards |
| calculated_at     | TIMESTAMP | Calculation time               |

## emails

| Field          | Type      | Description                                             |
| -------------- | --------- | ------------------------------------------------------- |
| id             | UUID      | Primary key                                             |
| application_id | UUID      | Application                                             |
| type           | ENUM      | APPLICATION, INTERVIEW, SELECTED, REJECTED, TALENT_POOL |
| recipient      | VARCHAR   | Recipient email                                         |
| subject        | VARCHAR   | Email subject                                           |
| status         | ENUM      | PENDING, SENT, FAILED                                   |
| sent_at        | TIMESTAMP | Sending time                                            |
| created_at     | TIMESTAMP | Created time                                            |

## audit_logs

| Field       | Type      | Description      |
| ----------- | --------- | ---------------- |
| id          | UUID      | Primary key      |
| user_id     | UUID      | User             |
| action      | VARCHAR   | Action performed |
| entity_type | VARCHAR   | Entity type      |
| entity_id   | UUID      | Entity ID        |
| old_value   | JSONB     | Previous value   |
| new_value   | JSONB     | New value        |
| created_at  | TIMESTAMP | Action time      |

# Relationships

```text
users
  │
  ├── jobs
  ├── screening_results
  ├── application_status_history
  ├── interview_assignments
  ├── interview_scorecards
  └── audit_logs

jobs
  │
  └── applications
          │
          ├── candidate
          ├── cv_documents
          ├── screening_results
          ├── status_history
          ├── tracking_token
          └── interviews
                  │
                  ├── interview_assignments
                  ├── interview_scorecards
                  └── combined_score

candidates
  │
  ├── applications
  └── talent_pool
```

# pgvector Usage

The candidate embedding is stored directly inside PostgreSQL.

```text
candidates
    │
    ├── profile_data
    └── embedding VECTOR
                  ↓
              pgvector
                  ↓
          Talent Pool Search
                  ↓
             Job Matching
```

The embedding is used for **semantic candidate retrieval**, not for the final hiring decision.

# Decision Ownership

```text
LangGraph + Ollama
        ↓
AI Recommendation
        ↓
HR Review
        ↓
HR Override if required
        ↓
Final HR Decision
```

AI does not directly set `SELECTED` or `REJECTED`.
