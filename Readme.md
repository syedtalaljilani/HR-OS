# HR OS

AI-assisted HR recruitment platform. Candidates apply and track through public
pages; an email agent runs the interview conversation; AI screening parses CVs,
scores candidates against job requirements, and surfaces the top candidates to
HR.

## Features

- Candidate careers site: job list, apply with CV, apply/_track status page,
  and a public **reschedule** page for interviews (`/reschedule/[token]`).
- AI CV extraction + LangGraph evaluation pipeline (per-CV score, evidence,
  uncertainty, automatic shortlist/reject).
- Hiring pipeline: invite candidates, schedule interviews (email + reschedule
  link + remote-interview request), screen results, offers/rejections.
- Email reply agent: watches the mailbox, records candidate messages in the
  dashboard chat, drafts and sends replies (only once per message), sends
  interview reminders ~1 day before, re-invites after a missed interview.
- HR dashboard: candidates, applications, chat inbox, job assistant, audit log.

## Tech Stack

| Area            | Technology                                               |
| --------------- | -------------------------------------------------------- |
| Frontend        | Next.js 16 (App Router) + React 19 + TypeScript + Tailwind 4 |
| Backend         | FastAPI + SQLAlchemy 2 + Alembic                          |
| AI runtime      | Ollama (Qwen3) + LangGraph workflows                      |
| Database        | PostgreSQL 16 + pgvector                                  |
| Email (SMTP)    | Gmail app password                                        |
| Inbound (IMAP)  | Gmail (reply agent + chat)                                |
| Auth            | JWT (RBAC: admin / hr)                                    |

## Repository Layout

```
HR OS
├── apps/
│   ├── backend/            FastAPI API, models, migrations, services
│   │   ├── alembic/        Database migrations
│   │   └── app/
│   │       ├── api/routes/ REST + public endpoints
│   │       ├── core/       settings (app/db/.env), security
│   │       ├── db/         session, models, .env / .env.example
│   │       ├── schemas/    Pydantic request/response models
│   │       ├── scripts/    seed_users, etc.
│   │       └── services/   business logic (interview, reply agent, …)
│   └── frontend/           Next.js app
│       └── app/            (site) public pages, (app)/dashboard, _lib, _components
├── ai/                     Standalone LangGraph prototype (agents/graphs/prompts)
├── docker/                 PostgreSQL + pgvector compose file
└── tests/
```

## Prerequisites

- **Node.js 20+** (for the frontend) and **Python 3.12+** (backend)
- **Docker Desktop** running (for Postgres + pgvector)
- **Ollama** installed and running on `http://localhost:11434`
- A **Gmail account** with a 2FA **app password** for sending/receiving email
  (optional — email agent can be disabled)

## Quick Start

### 1. Start the database

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts PostgreSQL with pgvector on port `5432`
(user `hr`, password `1234`, db `hr_recruitment`).

### 2. Start Ollama and pull the models

```bash
ollama serve
ollama pull qwen3:latest
ollama pull qwen3:1.7b
# optional extras referenced by the default config:
ollama pull deepseek-ocr
ollama pull all-minilm
```

### 3. Backend

```bash
cd apps/backend
python -m venv .venv                 # or activate your conda env
# Windows: .venv\Scripts\activate   | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp app/db/.env.example app/db/.env   # then edit with real values (DB URL, SMTP/IMAP, JWT secret)

# Migrations + seed admin user
alembic upgrade head
python -m app.scripts.seed_users      # creates admin@hros.com / admin12345

# Run the API (Swagger UI at http://localhost:8000/docs)
uvicorn app.main:app --reload --port 8000
```

> The reply-agent scheduler and the screening queue worker start automatically
> inside the FastAPI process (no separate worker command needed).

### 4. Frontend

```bash
cd apps/frontend
npm install
cp .env.local.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                          # http://localhost:3000
```

### 5. Log in

Open http://localhost:3000, log in with the seeded account
(`admin@hros.com` / `admin12345`), then **change the password immediately**
(dashboard → your account / user settings).

## Environment Variables

### Backend — `apps/backend/app/db/.env`

See [`app/db/.env.example`](apps/backend/app/db/.env.example) — copy it and fill:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy Postgres URL, incl. password |
| `JWT_SECRET` | Long random secret — change in production |
| `OLLAMA_URL` | Default `http://localhost:11434` |
| `OLLAMA_MODEL` / `OLLAMA_EVALUATION_MODEL` | Qwen3 for general + screening |
| `EMAIL_MODEL` | Tiny model used for AI email drafting (`qwen3:1.7b`) |
| `PUBLIC_BASE_URL` | Base URL for candidate links (job invites, reschedule) |
| `EMAIL_ENABLED` | Master switch for outbound email (SMTP) |
| `SMTP_*` | Gmail host/port/user/**app password**/from name |
| `IMAP_ENABLED` | Master switch for inbound mailbox watching |
| `IMAP_*` | Gmail IMAP host/port/user/**app password**/folder |
| `REPLY_AGENT_ENABLED` / `REPLY_AGENT_INTERVAL_SECONDS` | Reply agent loop |
| `MISSED_INTERVIEW_GRACE_MINUTES` | Grace before re-invite after a missed interview |
| `AUTO_EVALUATE_ON_APPLY`, `AUTO_REJECT_THRESHOLD` / `AUTO_REJECT_FLOOR` | Auto-screening routing rules |
| `TALENT_POOL_INVITES_ON_PUBLISH` / `TALENT_POOL_INVITE_DAYS` | Auto invites on publish |
| `COMPANY_NAME`, `HR_NAME`, `COMPANY_LOCATION` | Signed email identity (also editable in dashboard Settings) |

### Frontend — `apps/frontend/.env.local`

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend origin, e.g. `http://localhost:8000` |

## Email setup (Gmail)

1. Enable 2-Factor Authentication on the Gmail account that will send/receive.
2. Create an **App Password**: Google Account → Security → App passwords.
3. In Gmail enable IMAP: Settings → Forwarding and POP/IMAP → **Enable IMAP**.
4. Put the 16-character app password (spaces included) in both `SMTP_PASSWORD`
   and `IMAP_PASSWORD`.
5. Set `EMAIL_ENABLED=true` and `IMAP_ENABLED=true`.

The reply agent and the dashboard "Check inbox" button both use IMAP. It only
ever looks at recent mails (last 30 days) addressed to `IMAP_USER` and filters
by known candidates / recent outbound subjects, so personal mail is ignored.

## Database Migrations

```bash
cd apps/backend
alembic upgrade head        # apply migrations
alembic revision --autogenerate -m "describe change"   # create a new one
alembic downgrade -1        # roll back one step
```

## Public candidate flows

| URL | Purpose |
| --- | --- |
| `/` | Job listings |
| `/jobs/[id]` | Job detail |
| `/apply/[token]` | Public application form |
| `/track` | Application status by tracking token |
| `/reschedule/[token]` | Interview reschedule / remote-interview request |

When HR schedules an interview, the candidate's invite email includes a
reschedule link. Clicking it opens the slots; picking one cancels the old
interview and schedules a new one automatically. The candidate can also request
a remote interview, which HR accepts (sets the meeting link) or declines from
the candidate's dashboard page.

## Health checks

- `http://localhost:8000/health` — API status
- `http://localhost:8000/health/db` — database connectivity
- `http://localhost:8000/docs` — interactive Swagger API docs

## Lint / typecheck

```bash
# backend: import check (no dedicated linter configured)
python -c "import app.main"

# frontend
cd apps/frontend
npm run lint                              # eslint
npx tsc --noEmit -p tsconfig.json         # typecheck
```

## Troubleshooting

- **DB connection refused** — docker compose up, wait a few seconds for
  Postgres to accept connections, then `alembic upgrade head`.
- **Ollama errors / empty AI responses** — confirm `ollama serve` is running
  and every model in `.env` was pulled (`ollama list`).
- **Emails not sending** — the app password (not the normal Gmail password),
  2FA on, `EMAIL_ENABLED=true`, SMTP ports open.
- **No inbound messages in chat** — IMAP enabled + `IMAP_ENABLED=true`,
  `IMAP_FOLDER=INBOX`, messages addressed to `IMAP_USER` from within the last
  30 days.
- **Port 8000 already in use** — the dev backend runs with `--reload`; if you
  started it manually, stop the old process first.
- **Interview emails mention localhost** — set `PUBLIC_BASE_URL` to the
  address candidates will actually reach.