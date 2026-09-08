hr-os/
│
├── apps/
│   │
│   ├── web/                              # Next.js frontend
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   └── login/
│   │   │   ├── candidate/
│   │   │   │   ├── apply/
│   │   │   │   └── application/
│   │   │   ├── hr/
│   │   │   │   ├── dashboard/
│   │   │   │   ├── jobs/
│   │   │   │   ├── applications/
│   │   │   │   ├── candidates/
│   │   │   │   ├── interviews/
│   │   │   │   └── talent-pool/
│   │   │   ├── interviewer/
│   │   │   │   ├── dashboard/
│   │   │   │   └── interviews/
│   │   │   └── api/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── public/
│   │
│   └── backend/                          # FastAPI backend
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   │
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   └── routes/
│       │   │       ├── auth.py
│       │   │       ├── users.py
│       │   │       ├── jobs.py
│       │   │       ├── applications.py
│       │   │       ├── candidates.py
│       │   │       ├── interviews.py
│       │   │       ├── talent_pool.py
│       │   │       ├── emails.py
│       │   │       └── files.py
│       │   │
│       │   ├── core/
│       │   │   ├── config.py
│       │   │   ├── security.py
│       │   │   └── dependencies.py
│       │   │
│       │   ├── db/
│       │   │   ├── database.py
│       │   │   └── session.py
│       │   │
│       │   ├── models/
│       │   │   ├── user.py
│       │   │   ├── job.py
│       │   │   ├── candidate.py
│       │   │   ├── application.py
│       │   │   ├── cv_document.py
│       │   │   ├── screening.py
│       │   │   ├── interview.py
│       │   │   ├── scorecard.py
│       │   │   ├── talent_pool.py
│       │   │   ├── email.py
│       │   │   └── audit_log.py
│       │   │
│       │   ├── schemas/
│       │   │   ├── auth.py
│       │   │   ├── user.py
│       │   │   ├── job.py
│       │   │   ├── application.py
│       │   │   ├── candidate.py
│       │   │   ├── interview.py
│       │   │   ├── scorecard.py
│       │   │   └── talent_pool.py
│       │   │
│       │   ├── services/
│       │   │   ├── auth_service.py
│       │   │   ├── job_service.py
│       │   │   ├── application_service.py
│       │   │   ├── candidate_service.py
│       │   │   ├── interview_service.py
│       │   │   ├── talent_pool_service.py
│       │   │   ├── email_service.py
│       │   │   └── file_service.py
│       │   │
│       │   └── utils/
│       │       ├── tokens.py
│       │       ├── hashing.py
│       │       └── validators.py
│       │
│       ├── tests/
│       │   ├── unit/
│       │   └── integration/
│       │
│       ├── requirements.txt
│       ├── .env
│       └── .gitignore
│
├── ai/                                    # LangGraph AI system
│   ├── graphs/
│   │   ├── recruitment.py
│   │   ├── screening.py
│   │   └── talent_pool.py
│   │
│   ├── nodes/
│   │   ├── cv_extraction.py
│   │   ├── cv_validation.py
│   │   ├── requirement_extraction.py
│   │   ├── matching.py
│   │   ├── evidence.py
│   │   ├── uncertainty.py
│   │   ├── ranking.py
│   │   └── feedback.py
│   │
│   ├── prompts/
│   │   ├── cv_extraction.py
│   │   ├── cv_validation.py
│   │   ├── matching.py
│   │   ├── ranking.py
│   │   └── feedback.py
│   │
│   ├── schemas/
│   │   ├── candidate.py
│   │   ├── matching.py
│   │   └── screening.py
│   │
│   ├── models/
│   │   └── qwen.py
│   │
│   └── ollama/
│       └── client.py
│
├── storage/
│   ├── uploads/
│   └── processed/
│
├── tests/
│   ├── e2e/
│   ├── evaluation/
│   └── fixtures/
│
├── docs/
│   ├── discovery/
│   ├── architecture.md
│   ├── evaluation.md
│   ├── ai-workflow.md
│   ├── prompts.md
│   └── setup.md
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.web
│   └── nginx.conf
│
├── .env.example
├── docker-compose.yml
├── README.md
└── .gitignore