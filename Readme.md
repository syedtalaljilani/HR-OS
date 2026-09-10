# HR OS — AI-Native Recruitment Operating System

> End-to-end hiring platform where a local, private AI stack runs the busywork:
> it reads every CV, screens candidates against your job requirements, runs the
> email conversation, sends reminders, and auto-invites your talent pool — while
> humans stay in control of every final decision.

Built with **FastAPI + PostgreSQL** on the backend, **Next.js + TypeScript** on
the frontend, and **Ollama** running **Qwen3** models locally — no cloud AI
calls, no candidate data leaving your machine.

---

## Highlights

- **AI CV reading with OCR** — native text layers are parsed instantly (fast
  path); scanned/image-only PDFs are OCR'd on-device with `deepseek-ocr`
  (page-by-page for reliable output) and then structured into a profile.
- **LangGraph screening pipeline** — a 7-node reasoning graph scores each CV
  against job requirements: requirement extraction, evidence verification,
  matching, uncertainty detection, recommendation and validation. Ambiguous
  results can trigger an optional second-pass model.
- **Self-running reply agent** — watches your inbox (IMAP), logs candidate
  replies into the dashboard chat, drafts and sends replies exactly **once per
  message**, sends reminders the day before interviews, re-invites candidates
  who miss an interview, and cancels the remaining pipeline once someone is
  selected.
- **Human-in-the-loop interviews** — candidates can request a **remote**
  interview or propose a **specific new date/time** via email; the machine
  parses their message (natural-language date/time, timezone-aware) and HR
  reviews and accepts/declines from the dashboard. No autopilot on decisions.
- **Talent pool automation** — when a job is published, matching saved
  candidates are automatically emailed a **14-day invite link**.
- **Public careers site** — job board, invite-gated application form, status
  tracking by token, and a **public interview reschedule** page.
- **Complete HR console** — KPIs, ranked candidate shortlists, screening queue
  with retries, chat inbox, audit log, soft-delete/recover, user management.

---

## Architecture

```
                          ┌────────────────────────────────────────────┐
                          │                 PostgreSQL 16               │
                          │         + pgvector (embeddings)            │
                          └──────────────────▲─────────────────────────┘
                                             │ SQLAlchemy 2 / Alembic
┌───────────────────┐      ┌──────────────────┴──────────────────────────┐
│  Public (site)    │      │               FastAPI backend               │
│  /apply /track    │─────▶│  api/routes · services · schemas           │
│  /reschedule      │ JWT  │                                            │
│  job board        │      │  ┌──────────────┐  ┌────────────────────┐   │
└───────────────────┘      │  │Reply agent   │  │Screening queue     │   │
                           │  │(background   │  │worker (in-process) │   │
┌───────────────────┐      │  │ loop + IMAP)  │  └────────────────────┘   │
│  HR console       │◀────▶│  │· chat sync   │  ┌────────────────────┐   │
│  dashboard/chat   │      │  │· auto-reply  │  │CV extraction       │   │
│  screening queue  │      │  │· reminders   │  │· fast path (text)  │   │
│  talent pool      │      │  │· reschedule  │  │· deepseek-ocr      │   │
│  settings/audit   │      │  └──────────────┘  │· profile cache     │   │
└───────────────────┘      │                     └────────────────────┘   │
                           └──────────────────▲──────────────────────────┘
                                              │ localhost only
                                    ┌─────────┴──────────┐
                                    │   Ollama (11434)    │
                                    │ qwen3:latest (8B)   │
                                    │ qwen3:1.7b email    │
                                    │ deepseek-ocr        │
                                    │ all-minilm (embed)  │
                                    └─────────────────────┘
```

## Tech Stack

| Area               | Technology                                                          |
| ------------------ | ------------------------------------------------------------------- |
| Frontend           | Next.js 16 (App Router) · React 19 · TypeScript · Tailwind 4        |
| Backend            | FastAPI · SQLAlchemy 2 · Alembic · pydantic-settings · psycopg      |
| Document parsing   | PyMuPDF (text layer + page rendering) · python-docx                 |
| AI pipeline        | Ollama · Qwen3-8B (screening/parsing) · Qwen3-1.7B (email)          |
| OCR                | `deepseek-ocr` — sequential, DPI-limited, warm on startup           |
| Orchestration      | LangGraph (screening / email / job-assistant graphs)                |
| Database           | PostgreSQL 16 + pgvector                                            |
| Email              | SMTP (Gmail app password) + IMAP (inbound reply agent)              |
| Auth               | JWT · RBAC (ADMIN / HR / INTERVIEWER)                               |
| Tests              | pytest (38 tests) — extraction, OCR helpers, slot parser, AI client |

## Repository Layout

```
HR OS
├── apps/
│   ├── backend/               FastAPI API + services + migrations
│   │   ├── alembic/versions/  Database migrations (16+)
│   │   ├── app/api/routes/    REST + public + auth endpoints
│   │   ├── app/services/      extraction · screening · reply agent ·
│   │   │                      interview · email · talent pool · … 
│   │   ├── app/db/            session, models, .env / .env.example
│   │   ├── app/scripts/       seed_users, …
│   │   └── tests/             pytest suite (runs offline, mocked AI)
│   └── frontend/              Next.js app
│       └── app/               (site) public pages · (app)/dashboard · _lib
├── ai/                        LangGraph prototypes (graphs · nodes · prompts)
├── docker/                    PostgreSQL + pgvector compose file
└── docs/                      architecture, API routes, planning notes
```

## Quick Start

### 1. Database

```bash
docker compose -f docker/docker-compose.yml up -d
```

Postgres + pgvector on port `5432` (user `hr`, password `1234`, db `hr_recruitment`).

### 2. Ollama models

```bash
ollama serve
ollama pull qwen3:latest     # 8B — screening + general + profile parsing
ollama pull qwen3:1.7b       # email drafting
ollama pull deepseek-ocr     # scanned-CV OCR
ollama pull all-minilm       # embeddings (talent pool matching)
```

### 3. Backend

```bash
cd apps/backend
python -m venv .venv
# Windows: .venv\Scripts\activate   | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp app/db/.env.example app/db/.env   # edit: DB URL, SMTP/IMAP, JWT secret
alembic upgrade head                 # apply migrations
python -m app.scripts.seed_users     # admin@hros.com / admin12345

uvicorn app.main:app --reload --port 8000
```

The reply-agent scheduler and the screening-queue worker start automatically
inside the FastAPI process — no separate worker commands.

### 4. Frontend

```bash
cd apps/frontend
npm install
cp .env.local.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                         # http://localhost:3000
```

### 5. Log in

Open http://localhost:3000 → sign in with the seeded account
(`admin@hros.com` / `admin12345`).

## How the AI Pipeline Works

**CV extraction** reads the file once, from whichever comes first:

| Path    | When                                   | How                                                        |
| ------- | -------------------------------------- | ---------------------------------------------------------- |
| Fast    | PDF/DOCX/TXT with a native text layer  | direct extraction, no AI call — milliseconds                 |
| OCR     | scanned / image-only PDFs              | pages rendered (max 5, DPI 150) and OCR'd **one at a time** with `deepseek-ocr`, then marker-cleaned   |
| Cache   | same file re-uploaded (SHA-256)        | stored profile returned instantly                          |

Results are validated, and unmatched information (or missing fields) is
surfaced to HR rather than silently guessed.

**Screening** runs a LangGraph of 7 sequential nodes — requirements, evidence
verification, matching, uncertainty, recommendation, validation — returning a
**score (0–100)**, per-requirement evidence (`MATCH`/`PARTIAL`/`MISSING`/
`UNCLEAR`) and an automatic shortlist or rejection (thresholds 40/20 are
configurable). Ambiguous runs may trigger a bounded legacy fallback so every CV
gets a result even while Ollama is cold.

**The reply agent** reads candidate emails (IMAP, last 30 days, filtered to
known candidates/recent outbound subjects), stores them in dashboard chat,
answers each message at most once, reminds before interviews, re-invites after
missed ones (15 min grace), and parses candidate-proposed **new interview
slots** (`NEW_SLOT`) or **remote-interview** requests — these need HR approval
from the dashboard, never auto-accepted.

## Environment Variables

Backend lives in `apps/backend/app/db/.env` — see `.env.example`. Key ones:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy Postgres URL |
| `JWT_SECRET` | long random secret — change in production |
| `OLLAMA_URL` / `OLLAMA_MODEL` | AI runtime + screening/general model |
| `EMAIL_MODEL` | tiny model for email drafting (`qwen3:1.7b`) |
| `OLLAMA_OCR_MODEL` / `OCR_MAX_PAGES` / `OCR_DPI` | scanned-CV OCR settings |
| `PUBLIC_BASE_URL` | origin used in candidate-facing links |
| `SMTP_*` / `IMAP_*` | Gmail sending + inbound mailbox (app password) |
| `REPLY_AGENT_*` | reply loop interval, missed-interview grace |
| `AUTO_EVALUATE_ON_APPLY` / `AUTO_REJECT_*` | auto-screening routing |
| `TALENT_POOL_INVITES_ON_PUBLISH` / `TALENT_POOL_INVITE_DAYS` | pool automation |
| `COMPANY_NAME` / `HR_NAME` / `COMPANY_LOCATION` | email identity (also in Settings UI) |

Frontend: `apps/frontend/.env.local` → `NEXT_PUBLIC_API_URL`.

## Email Setup (Gmail)

1. Enable 2FA on the Gmail account, then create an **App Password**
   (Google Account → Security → App passwords).
2. Enable **IMAP** in Gmail settings (Forwarding and POP/IMAP → Enable IMAP).
3. Set `SMTP_USER`, `SMTP_PASSWORD`, `IMAP_USER`, `IMAP_PASSWORD` to that
   account + app password; `EMAIL_ENABLED=true`, `IMAP_ENABLED=true`.

The agent only looks at recent mail (last 30 days) addressed to `IMAP_USER`
and filters by known candidates / recent outbound subjects — personal mail is
ignored.

## Candidate Flows

| URL | Purpose |
| --- | --- |
| `/` | Public job listings |
| `/jobs/[id]` | Job detail |
| `/apply/[token]` | Invite-gated application form (CV upload + consent) |
| `/track` | Application status by tracking token |
| `/reschedule/[token]` | Reschedule / request a remote interview |

When HR schedules an interview, the invite email carries a reschedule link.
Candidates can pick a new slot themselves or request a **remote** meeting or a
**new date/time** — all surfaced in dashboard chat for HR review, then
accepted/declined with one click.

## Health & Docs

- `GET /health` — API status
- `GET /health/db` — database connectivity
- `GET /docs` — interactive Swagger API documentation

## Testing

```bash
cd apps/backend
python -m pytest            # 38 tests, ~1s, fully offline (AI is mocked)
```

Covers CV text extraction & OCR fallback, profile parsing fallbacks, cache
behaviour, OCR marker cleanup, slot-parser intent/date/time cases (Karachi→UTC)
and the AI-client payloads.

Lint / typecheck:

```bash
# frontend
cd apps/frontend
npm run lint
npx tsc --noEmit -p tsconfig.json
# backend
python -c "import app.main"
```

## Troubleshooting

- **DB connection refused** — `docker compose up -d`, wait a few seconds, then `alembic upgrade head`.
- **Ollama errors / empty AI output** — confirm `ollama serve` is up and every model in `.env` is in `ollama list`.
- **Emails not sending** — must be an **app password** (not the normal password), 2FA on, `EMAIL_ENABLED=true`.
- **No inbound messages in chat** — IMAP enabled, `IMAP_FOLDER=INBOX`, replies within the last 30 days.
- **Scanned CVs return nothing** — `deepseek-ocr` must be pulled; OCR is limited to `OCR_MAX_PAGES` pages.
- **Candidate links mention localhost** — set `PUBLIC_BASE_URL` to the real public origin.