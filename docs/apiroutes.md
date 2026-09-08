# HR Recruitment OS API Routes

| Method | Route                                    | Purpose                      |
| ------ | ---------------------------------------- | ---------------------------- |
| POST   | `/auth/login`                            | HR/Admin login               |
| POST   | `/auth/logout`                           | Logout                       |
| GET    | `/auth/me`                               | Current user                 |
| POST   | `/users`                                 | Create HR/Interviewer user   |
| GET    | `/users`                                 | List users                   |
| PATCH  | `/users/:id`                             | Update user                  |
| POST   | `/jobs`                                  | Create job                   |
| GET    | `/jobs`                                  | List jobs                    |
| GET    | `/jobs/:id`                              | Get job                      |
| PATCH  | `/jobs/:id`                              | Update job                   |
| POST   | `/jobs/:id/publish`                      | Publish job                  |
| POST   | `/public/jobs/:id/apply`                 | Candidate application        |
| GET    | `/public/applications/:token`            | Candidate tracking           |
| POST   | `/applications/:id/process`              | Process CV                   |
| GET    | `/applications/:id`                      | Get application              |
| GET    | `/applications`                          | List applications            |
| PATCH  | `/applications/:id/status`               | Update status                |
| POST   | `/applications/:id/screen`               | Run AI screening             |
| POST   | `/applications/:id/override`             | HR override AI result        |
| GET    | `/candidates/:id`                        | Candidate details            |
| GET    | `/candidates`                            | List candidates              |
| POST   | `/talent-pool/:candidateId`              | Add candidate to Talent Pool |
| GET    | `/talent-pool`                           | Search Talent Pool           |
| POST   | `/talent-pool/match`                     | Match candidates with job    |
| POST   | `/talent-pool/:id/contact`               | Contact candidate            |
| POST   | `/talent-pool/:id/interest`              | Record candidate interest    |
| POST   | `/interviews`                            | Schedule interview           |
| GET    | `/interviews/:id`                        | Interview details            |
| POST   | `/interviews/:id/assign`                 | Assign interviewer           |
| GET    | `/interviews/:id/assignments`            | List interviewers            |
| POST   | `/interviews/:id/scorecard`              | Submit scorecard             |
| GET    | `/interviews/:id/scorecards`             | View scorecards              |
| GET    | `/interviews/:id/score`                  | Calculate combined score     |
| PATCH  | `/interviews/:id/scorecard/:scorecardId` | Correct scorecard            |
| GET    | `/applications/:id/history`              | Status history               |
| POST   | `/applications/:id/feedback`             | Generate feedback draft      |
| POST   | `/applications/:id/decision`             | HR final decision            |
| POST   | `/applications/:id/email`                | Send approved email          |
| GET    | `/audit-logs`                            | View audit logs              |
