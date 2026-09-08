# HR Recruitment OS API Contracts

## Authentication

| Method | Route          | Access        | Purpose      |
| ------ | -------------- | ------------- | ------------ |
| POST   | `/auth/login`  | Public        | Login        |
| POST   | `/auth/logout` | Authenticated | Logout       |
| GET    | `/auth/me`     | Authenticated | Current user |

## Users

| Method | Route        | Access    | Purpose     |
| ------ | ------------ | --------- | ----------- |
| POST   | `/users`     | ADMIN, HR | Create user |
| GET    | `/users`     | ADMIN, HR | List users  |
| GET    | `/users/:id` | ADMIN, HR | Get user    |
| PATCH  | `/users/:id` | ADMIN, HR | Update user |

## Jobs

| Method | Route               | Access    | Purpose     |
| ------ | ------------------- | --------- | ----------- |
| POST   | `/jobs`             | HR, ADMIN | Create job  |
| GET    | `/jobs`             | HR, ADMIN | List jobs   |
| GET    | `/jobs/:id`         | HR, ADMIN | Get job     |
| PATCH  | `/jobs/:id`         | HR, ADMIN | Update job  |
| POST   | `/jobs/:id/publish` | HR, ADMIN | Publish job |
| POST   | `/jobs/:id/close`   | HR, ADMIN | Close job   |

## Public Candidate Application

| Method | Route                         | Access | Purpose            |
| ------ | ----------------------------- | ------ | ------------------ |
| GET    | `/public/jobs/:id`            | Public | View job           |
| POST   | `/public/jobs/:id/apply`      | Public | Submit application |
| GET    | `/public/applications/:token` | Token  | Track application  |

### Application Request

```json
{
  "fullName": "Candidate Name",
  "email": "candidate@example.com",
  "phone": "+92XXXXXXXXXX",
  "expectedSalary": 120000,
  "consent": true
}
```

CV is uploaded as multipart form data.

### Application Response

```json
{
  "applicationId": "APP-2026-00421",
  "status": "APPLIED",
  "trackingUrl": "/application/secure-token"
}
```

## Applications

| Method | Route                        | Access    | Purpose                    |
| ------ | ---------------------------- | --------- | -------------------------- |
| GET    | `/applications`              | HR, ADMIN | List applications          |
| GET    | `/applications/:id`          | HR, ADMIN | Application details        |
| POST   | `/applications/:id/process`  | HR, ADMIN | Process CV                 |
| POST   | `/applications/:id/screen`   | HR, ADMIN | Run AI screening           |
| POST   | `/applications/:id/override` | HR, ADMIN | Override AI recommendation |
| PATCH  | `/applications/:id/status`   | HR, ADMIN | Change status              |
| GET    | `/applications/:id/history`  | HR, ADMIN | Status history             |

## AI Screening

### Request

```json
{
  "applicationId": "uuid"
}
```

### Response

```json
{
  "recommendation": "MATCH",
  "score": 87,
  "evidence": [
    {
      "requirement": "3+ years Python",
      "status": "MATCH",
      "evidence": "4 years Python experience"
    }
  ],
  "missingRequirements": [],
  "uncertainty": []
}
```

AI result is stored in `screening_results`.

HR can accept or override the recommendation.

## Candidates

| Method | Route             | Access    | Purpose           |
| ------ | ----------------- | --------- | ----------------- |
| GET    | `/candidates`     | HR, ADMIN | List candidates   |
| GET    | `/candidates/:id` | HR, ADMIN | Candidate details |
| PATCH  | `/candidates/:id` | HR, ADMIN | Update candidate  |

## Talent Pool

| Method | Route                       | Access    | Purpose                |
| ------ | --------------------------- | --------- | ---------------------- |
| POST   | `/talent-pool/:candidateId` | HR, ADMIN | Add candidate          |
| GET    | `/talent-pool`              | HR, ADMIN | Search candidates      |
| POST   | `/talent-pool/match`        | HR, ADMIN | Match against job      |
| POST   | `/talent-pool/:id/contact`  | HR, ADMIN | Contact candidate      |
| PATCH  | `/talent-pool/:id/status`   | HR, ADMIN | Update interest status |

### Talent Pool Match

```json
{
  "jobId": "uuid",
  "limit": 20
}
```

Response:

```json
{
  "matches": [
    {
      "candidateId": "uuid",
      "similarity": 0.91,
      "candidateName": "Candidate Name"
    }
  ]
}
```

pgvector handles candidate retrieval. LangGraph can then evaluate the retrieved candidates against the job requirements.

## Interviews

| Method | Route                         | Access                          | Purpose            |
| ------ | ----------------------------- | ------------------------------- | ------------------ |
| POST   | `/interviews`                 | HR, ADMIN                       | Schedule interview |
| GET    | `/interviews/:id`             | HR, ADMIN, Assigned Interviewer | View interview     |
| PATCH  | `/interviews/:id`             | HR, ADMIN                       | Update interview   |
| POST   | `/interviews/:id/assign`      | HR, ADMIN                       | Assign interviewer |
| GET    | `/interviews/:id/assignments` | HR, ADMIN                       | View assignments   |

### Schedule Interview

```json
{
  "applicationId": "uuid",
  "type": "TECHNICAL",
  "scheduledAt": "2026-09-15T14:00:00+05:00"
}
```

## Interview Scorecards

| Method | Route                                    | Access               | Purpose            |
| ------ | ---------------------------------------- | -------------------- | ------------------ |
| POST   | `/interviews/:id/scorecard`              | Assigned Interviewer | Submit score       |
| GET    | `/interviews/:id/scorecards`             | HR, ADMIN            | View all scores    |
| PATCH  | `/interviews/:id/scorecard/:scorecardId` | Authorized User      | Correct score      |
| GET    | `/interviews/:id/score`                  | HR, ADMIN            | Get combined score |

### Technical Scorecard

```json
{
  "technicalKnowledge": 22,
  "problemSolving": 17,
  "practicalExperience": 18,
  "roleSpecificSkills": 16,
  "technicalCommunication": 13,
  "comments": "Strong practical experience."
}
```

Backend calculates the total:

```text
22 + 17 + 18 + 16 + 13 = 86 / 100
```

The combined score is calculated from individual interviewer scores.

## Final Decision

| Method | Route                        | Access    | Purpose        |
| ------ | ---------------------------- | --------- | -------------- |
| POST   | `/applications/:id/decision` | HR, ADMIN | Final decision |

### Request

```json
{
  "decision": "SELECTED",
  "joiningDate": "2026-10-01",
  "reason": "Strong technical and HR interview performance"
}
```

Allowed decisions:

```text
SELECTED
HOLD
REJECTED
```

The API must reject final decisions coming from AI services.

## Candidate Feedback

| Method | Route                                | Access    | Purpose                 |
| ------ | ------------------------------------ | --------- | ----------------------- |
| POST   | `/applications/:id/feedback`         | HR, ADMIN | Generate feedback draft |
| PATCH  | `/applications/:id/feedback`         | HR, ADMIN | Edit feedback           |
| POST   | `/applications/:id/feedback/approve` | HR, ADMIN | Approve feedback        |

Rejected candidate feedback must be reviewed and approved by HR before sending.

## Emails

| Method | Route                      | Access    | Purpose             |
| ------ | -------------------------- | --------- | ------------------- |
| POST   | `/applications/:id/email`  | HR, ADMIN | Send approved email |
| GET    | `/applications/:id/emails` | HR, ADMIN | Email history       |

## Audit Logs

| Method | Route                       | Access    | Purpose             |
| ------ | --------------------------- | --------- | ------------------- |
| GET    | `/audit-logs`               | ADMIN     | View audit history  |
| GET    | `/applications/:id/history` | HR, ADMIN | Application history |

## API Rules

### Authentication

HR and Admin APIs require authenticated sessions.

### Authorization

```text
ADMIN
    ↓
Full system access

HR
    ↓
Recruitment operations

INTERVIEWER
    ↓
Assigned interviews only
```

### Candidate Security

Candidates do not have accounts.

Application tracking uses a secure random token.

```text
/public/applications/:token
```

The token should be:

```text
Random
Hashed in database
Expirable
Revocable
Rate limited
```

Internal database IDs must not be exposed as authentication credentials.

## API Responsibility

```text
Next.js
    ↓
FastAPI
    ↓
├── PostgreSQL
├── Redis / BullMQ
├── File Storage
└── LangGraph
        ↓
      Ollama
        ↓
       Qwen
```

The backend owns authentication, authorization, database operations, status transitions, score calculations and final decision control.

LangGraph owns AI workflow execution and recommendations.
