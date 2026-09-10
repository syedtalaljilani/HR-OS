# HR OS — Working Memory (auto-maintained)

## Objective
- Candidate email Chat: replies must appear in the chat, be answered **once** per message, and actually answer the candidate's query; interview invitation email goes out **once** per real status transition; one interview reminder/follow-up sent **~1 day before** the interview (once); Chat application link must work; Chat page responsive; chat tab removed from candidate view.

## Important Details
- User writes in Roman Urdu; UI copy stays English.
- `candidates/[id]` page param = **application id** (fetches `/applications/${id}`). Links must use `application_id`.
- Backend runs via `uvicorn --reload` (PID 34952 owns port 8000) — service `.py` edits hot-reload automatically. Do NOT manually restart; file save is enough.
- Commands: python = `C:\Users\ic\anaconda3\envs\HROS\python.exe`, backend workdir `D:\Developement\AI OS\HR OS\apps\backend`, `$env:PYTHONPATH="...\apps\backend"`. Inline `python -c` breaks in PowerShell — use temp scripts (dir `C:\Users\ic\AppData\Local\Temp\opencode\diag*.py`). Frontend workdir `...\apps\frontend`: `node_modules\.bin\tsc.cmd --noEmit -p tsconfig.json`, `node_modules\.bin\eslint.cmd`.
- IMAP filter (`_inbox_filters`): date-based `SINCE` 30 days (NOT UNSEEN — a read-but-\Seen candidate reply must still show). Two parts OR-ed: `FROM` known candidates + `SUBJECT` matching recent outbound subjects. SEARCH must stay small — Gmail rejects oversized OR-chains (`BAD Could not parse command`). Current guards: uniqued subjects, budget ~800 chars, max 40 terms, sanitized (no `"`/`\`/control) via `_or_chain._term`.
- Dedupe (`_store_inbound`): now checks **any existing** INBOUND row with same `recipient`, direction INBOUND, subject (**trimmed/-fallback `(no subject)`**), and body (**cleaned**) → returns `None` → `handle_reply` rolls back and skips draft/send. Do NOT revert to "compare only vs latest" — that caused every tick to re-store all distinct messages and re-send a reply flood (45 dup inbound rows / ~40 dup outbound emails in one hour).
- Inbound stored with **cleaned** body (`_clean_query`); `db.commit()` right after store, before AI draft/send. AI reply prompt answers the actual most-recent question in the message's language, never repeats the invitation.
- Interview reminder: fires once per interview when `SCHEDULED`, `reminder_sent_at IS NULL`, `now-24h <= scheduled_at`, `scheduled_at > now`. Reuses `EmailType.INTERVIEW`, subject `Interview Reminder for {job_title}`, audit action `interview.reminder`. Wired into `run_auto_agent` (returns `{"missed","reminders","inbox","delivery"}`) + scheduler tick log.
- `schedule_interview` (`applications.py`) NO `force_email=True` → invitation emails only on real transition (once). Migration `a7b8c9d0e1f2` (add `interviews.reminder_sent_at`) APPLIED (head).
- Test data: candidate SYED TALAL JILANI (`d0b15997…`, `syedtalalj@gmail.com`); app `c59b5052-2330-484d-a82c-4eea5d9df5d7`; interview `7ce37943-d942-4faa-b559-4fbf8c8e52c1` 2026-09-10 03:00 UTC (08:00 PKT), reminder sent `reminder_sent_at` set 00:38 UTC. Two duplicate SCHEDULED rows (c15ecae8, b5ba117c) CANCELLED (had 3 identical from 3 schedule clicks). Company: Kanzo Ag, Phase-2 Industrial Estate, Multan.
- Chat thread test state (post-cleanup): application-received ×2, invitations ×3, replies ×3 (`Re: Interview Invitation - Computer Intern`, `Re: Interview Confirmation`, `Re: Computer Intern Interview`), reminder ×1. 3 real inbound candidate messages; re-fetch = 0 sends (all deduped).
- Candidate's Gmail has 3 real replies (all `\Seen`, ids 24380/24382/24383). Gmail inbox ~22k unseen personal messages — narrow filter is intentional.
- `.env` IMAP: `IMAP_ENABLED=true`, Gmail app password `dfca rnlr omab ryiu`, sender `syedtalaljani.dev@gmail.com`.

## Work State
### Completed
- Tie-chat on `candidates/[id]` removed (tab union/TABS/state/poll fn `checkInbox`/`sendChatMessage`/`aiReplySuggestion`, chat JSX, unused imports). Kept `inputClass` + `draftEmailWithAI` (email-assist modal). tsc+eslint clean.
- Chat page fixed: "Open application" → `applications/${selected.application_id}` (was candidate_id); responsive: `min-h-0` on scroll areas, `md:grid-rows-[minmax(0,1fr)]`, `md:grid-cols-[23rem_minmax(0,1fr)]`, heights `h-[calc(100dvh-16rem)] md:h-[calc(100dvh-12rem)] lg:h-[calc(100dvh-10rem)]`, `shrink-0` tab bar. tsc+eslint clean.
- Reply-root-cause fixed + verified live: SINCE filter, commit-before-draft, ANY-match dedupe, `_clean_query`, sharpened prompt, SEARCH size caps/sanitization. Live re-fetch: 0 sends.
- Interview reminder feature: model column, migration applied, `send_interview_reminders`, `run_auto_agent` + scheduler wiring, `force_email` removed. Verified live: 1 reminder sent, duplicates cancelled.
- Data cleanup: 46→3 inbound; 45→18→9 outbound (12h); threads tidy.
- Earlier: Chat page + bell/notification panel in layout; `inbox.py` conversations/unread/read (`read_at` migration); delete/recover cascade.

### Active
- (none)

### Blocked
- (none)

## Next Move
- Watch next scheduler tick in the backend logs to confirm 0 sends (should be silent).
- If user re-reports Chat responsive issues, iterate on heights/grid from frontend.

## Relevant Files
- `apps/backend/app/services/reply_agent_service.py`: `_inbox_filters` (SINCE + capped/sanitized OR chain), `_clean_query`, `_store_inbound` (ANY-match dedupe), `handle_reply` (dup guard, commit-before-draft, prompt), `send_interview_reminders`, `run_auto_agent`.
- `apps/backend/app/api/routes/applications.py`: `schedule_interview` (no force_email).
- `apps/backend/app/db/models/interview.py`: `reminder_sent_at`.
- `apps/backend/alembic/versions/a7b8c9d0e1f2_add-interview-reminder.py`: applied.
- `apps/frontend/app/(app)/dashboard/chat/page.tsx`: application link + responsive.
- `apps/frontend/app/(app)/dashboard/candidates/[id]/page.tsx`: chat tab removed.
- `apps/backend/app/db/.env`: IMAP settings.
- Scrap diagnostics in `C:\Users\ic\AppData\Local\Temp\opencode\diag*.py`.