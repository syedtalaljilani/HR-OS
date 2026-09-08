"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import Badge from "@/app/hr/_components/Badge";
import Button from "@/app/hr/_components/Button";
import { Field, inputClass } from "@/app/hr/_components/Field";
import Modal, { ErrorNote } from "@/app/hr/_components/Modal";
import { LoadingScreen } from "@/app/hr/_components/Button";
import {
  api,
  formatDate,
  formatMoney,
  formatStatus,
  type ApplicationDetail,
  type EvidenceItem,
} from "@/app/hr/_lib/api";

const STATUSES = [
  "APPLIED",
  "PROCESSING",
  "HR_REVIEW",
  "SHORTLISTED",
  "INTERVIEW_SCHEDULED",
  "TECHNICAL_INTERVIEW",
  "TECHNICAL_REVIEW",
  "BEHAVIORAL_INTERVIEW",
  "FINAL_REVIEW",
  "SELECTED",
  "HOLD",
  "REJECTED",
];

const RECOMMENDATIONS = ["MATCH", "PARTIAL", "MISSING", "UNCLEAR"];
const EMAIL_TYPES = [
  "APPLICATION",
  "INTERVIEW",
  "SELECTED",
  "REJECTED",
  "TALENT_POOL",
];

type Action =
  | "process"
  | "screen"
  | "status"
  | "decision"
  | "override"
  | "talent"
  | "email"
  | null;

const EVIDENCE_COLORS: Record<EvidenceItem["status"], string> = {
  MATCH: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  PARTIAL: "bg-amber-50 text-amber-700 ring-amber-200",
  MISSING: "bg-rose-50 text-rose-700 ring-rose-200",
  UNCLEAR: "bg-zinc-100 text-zinc-600 ring-zinc-200",
};

function EvidenceGroup({ title, items }: { title: string; items: EvidenceItem[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h3>
      <ul className="mt-2 flex flex-col gap-2">
        {items.map((item) => (
          <li
            key={item.requirement}
            className=" border border-zinc-200 bg-white p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-medium text-zinc-900">
                {item.requirement}
              </p>
              <span
                className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${EVIDENCE_COLORS[item.status]}`}
              >
                {item.status}
              </span>
            </div>
            {item.evidence ? (
              <p className="mt-1.5 text-sm text-zinc-500">“{item.evidence}”</p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className=" border border-zinc-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-base font-semibold text-zinc-900">{title}</h2>
      {children}
    </section>
  );
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setDetail(await api<ApplicationDetail>(`/applications/${id}`));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load application");
    }
  }, [id]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  function openAction(next: Action) {
    setFormData({});
    setAction(next);
  }

  async function runAction() {
    if (!action || !detail) return;
    setBusy(true);
    try {
      if (action === "status") {
        await api(`/applications/${detail.id}/status`, {
          method: "PATCH",
          body: {
            status: formData.status ?? "HR_REVIEW",
            reason: formData.reason || null,
          },
        });
      } else if (action === "decision") {
        await api(`/applications/${detail.id}/decision`, {
          method: "POST",
          body: {
            decision: formData.decision ?? "HOLD",
            reason: formData.reason || null,
          },
        });
      } else if (action === "override") {
        await api(`/applications/${detail.id}/override`, {
          method: "POST",
          body: {
            recommendation: formData.recommendation ?? "PARTIAL",
            score: formData.score ? Number(formData.score) : null,
            note: formData.note || null,
          },
        });
      } else if (action === "talent") {
        await api(`/talent-pool/${detail.candidate_id}`, {
          method: "POST",
          body: { consent: true, source_application_id: detail.id },
        });
        setNotice("Candidate added to the talent pool.");
      } else if (action === "email") {
        await api(`/applications/${detail.id}/email`, {
          method: "POST",
          body: {
            type: formData.type ?? "INTERVIEW",
            subject: formData.subject || null,
            body: formData.body || null,
          },
        });
        setNotice("Email logged successfully.");
      } else if (action === "process") {
        await api(`/applications/${detail.id}/process`, { method: "POST" });
      } else if (action === "screen") {
        await api(`/applications/${detail.id}/screen`, { method: "POST" });
      }
      setAction(null);
      load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  if (error) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-8">
        <ErrorNote message={error} />
        <Link href="/dashboard/candidates" className="text-sm text-violet-600 hover:underline">
          ← Back to candidates
        </Link>
      </div>
    );
  }
  if (!detail) return <LoadingScreen />;

  const screening = detail.screening;
  const evidence =
    (screening?.evidence as { items?: EvidenceItem[] } | null)?.items ?? [];
  const missing =
    (screening?.missing_requirements as { items?: EvidenceItem[] } | null)?.items ?? [];
  const uncertain =
    (screening?.uncertainty as { items?: EvidenceItem[] } | null)?.items ?? [];

  const score = screening?.score ? Number(screening.score) : null;

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div>
        <Link
          href="/dashboard/candidates"
          className="text-sm text-zinc-500 hover:text-zinc-800"
        >
          ← Back to candidates
        </Link>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-zinc-900">
                {detail.candidate_name}
              </h1>
              <Badge status={detail.status} />
            </div>
            <p className="mt-1 text-sm text-zinc-500">
              {detail.application_id} • {detail.job_title}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              {detail.candidate_email}
              {detail.candidate_phone ? ` • ${detail.candidate_phone}` : ""}
              {detail.expected_salary
                ? ` • Expected ${formatMoney(detail.expected_salary)}`
                : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              loading={action === "process" && busy}
              onClick={() => openAction("process")}
              className="px-3 py-1.5"
            >
              Process CV
            </Button>
            <Button
              variant="secondary"
              loading={action === "screen" && busy}
              onClick={() => openAction("screen")}
              className="px-3 py-1.5"
            >
              Run AI screening
            </Button>
            <Button
              variant="secondary"
              onClick={() => openAction("status")}
              className="px-3 py-1.5"
            >
              Change status
            </Button>
            <Button
              variant="secondary"
              onClick={() => openAction("decision")}
              className="px-3 py-1.5"
            >
              Final decision
            </Button>
            <Button
              variant="secondary"
              onClick={() => openAction("override")}
              className="px-3 py-1.5"
            >
              Override
            </Button>
            <Button
              variant="secondary"
              onClick={() => openAction("talent")}
              className="px-3 py-1.5"
            >
              Add to talent pool
            </Button>
            <Button variant="secondary" onClick={() => openAction("email")} className="px-3 py-1.5">
              Send email
            </Button>
          </div>
        </div>
        {notice ? (
          <p className="mt-4  bg-emerald-50 px-4 py-3 text-sm text-emerald-700 ring-1 ring-inset ring-emerald-200">
            {notice}
          </p>
        ) : null}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="flex flex-col gap-6">
          <Section title="AI screening">
            {!screening ? (
              <p className="text-sm text-zinc-500">
                No screening result yet. Run AI screening to get a
                recommendation.
              </p>
            ) : (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                  <div className="flex flex-col items-center">
                    <span className="text-4xl font-bold text-violet-600">
                      {score ?? "–"}
                    </span>
                    <span className="text-xs text-zinc-400">match score</span>
                  </div>
                  <div className="flex flex-1 flex-col gap-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-600">Recommendation</span>
                      <Badge status={screening.recommendation ?? "UNCLEAR"} />
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-600">HR decision</span>
                      <span className="font-medium text-zinc-900">
                        {formatStatus(screening.hr_decision)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-600">Model</span>
                      <span className="font-mono text-xs text-zinc-500">
                        {screening.model ?? "—"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </Section>

          <Section title="Requirement matching">
            {evidence.length === 0 ? (
              <p className="text-sm text-zinc-500">
                No matching data available.
              </p>
            ) : (
              <div className="flex flex-col gap-6">
                <EvidenceGroup title="Matches" items={evidence} />
              </div>
            )}
          </Section>
        </div>

        <div className="flex flex-col gap-6">
          <Section title="Missing requirements">
            {missing.length === 0 ? (
              <p className="text-sm text-zinc-500">Nothing missing.</p>
            ) : (
              <EvidenceGroup title="Missing" items={missing} />
            )}
          </Section>

          <Section title="Uncertainty flags">
            {uncertain.length === 0 ? (
              <p className="text-sm text-zinc-500">No uncertainty flags.</p>
            ) : (
              <EvidenceGroup title="Uncertain" items={uncertain} />
            )}
          </Section>

          <Section title="CV documents">
            {detail.cv_documents.length === 0 ? (
              <p className="text-sm text-zinc-500">No CV uploaded.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {detail.cv_documents.map((doc) => (
                  <li
                    key={doc.id}
                    className="flex items-center justify-between  border border-zinc-200 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-zinc-900">
                        {doc.file_name}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {doc.mime_type} • uploaded {formatDate(doc.created_at)}
                      </p>
                    </div>
                    <Badge status={doc.extraction_status} />
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Status history">
            {detail.status_history.length === 0 ? (
              <p className="text-sm text-zinc-500">No history yet.</p>
            ) : (
              <ol className="flex flex-col gap-3">
                {detail.status_history.map((entry) => (
                  <li key={entry.id} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-violet-500" />
                      <span className="w-px flex-1 bg-zinc-200" />
                    </div>
                    <div className="mb-3 flex-1">
                      <p className="text-sm font-medium text-zinc-800">
                        {entry.from_status
                          ? `${formatStatus(entry.from_status)} → ${formatStatus(entry.to_status)}`
                          : formatStatus(entry.to_status)}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {formatDate(entry.created_at)}
                        {entry.reason ? ` — ${entry.reason}` : ""}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </Section>
        </div>
      </div>

      <Modal
        open={action !== null}
        onClose={() => setAction(null)}
        title={
          action === "status"
            ? "Change status"
            : action === "decision"
              ? "Final decision"
              : action === "override"
                ? "Override screening result"
                : action === "talent"
                  ? "Add to talent pool"
                  : action === "email"
                    ? "Send email"
                    : action === "screen"
                      ? "AI screening"
                      : "Process CV"
        }
      >
        <div className="flex flex-col gap-4">
          {action === "status" ? (
            <>
              <Field label="New status *">
                <select
                  value={formData.status ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, status: event.target.value })
                  }
                  className={inputClass()}
                >
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {formatStatus(status)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Reason">
                <input
                  value={formData.reason ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, reason: event.target.value })
                  }
                  className={inputClass()}
                />
              </Field>
            </>
          ) : null}

          {action === "decision" ? (
            <>
              <Field label="Decision *">
                <select
                  value={formData.decision ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, decision: event.target.value })
                  }
                  className={inputClass()}
                >
                  <option value="SELECTED">Selected</option>
                  <option value="HOLD">Hold</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </Field>
              <Field label="Reason">
                <input
                  value={formData.reason ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, reason: event.target.value })
                  }
                  className={inputClass()}
                />
              </Field>
            </>
          ) : null}

          {action === "override" ? (
            <>
              <Field label="New AI recommendation *">
                <select
                  value={formData.recommendation ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, recommendation: event.target.value })
                  }
                  className={inputClass()}
                >
                  {RECOMMENDATIONS.map((rec) => (
                    <option key={rec} value={rec}>
                      {rec}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Score (0–100)">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.score ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, score: event.target.value })
                  }
                  className={inputClass()}
                />
              </Field>
              <Field label="Note">
                <textarea
                  rows={3}
                  value={formData.note ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, note: event.target.value })
                  }
                  className={inputClass()}
                />
              </Field>
            </>
          ) : null}

          {action === "email" ? (
            <>
              <Field label="Email type *">
                <select
                  value={formData.type ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, type: event.target.value })
                  }
                  className={inputClass()}
                >
                  {EMAIL_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {formatStatus(type)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Subject">
                <input
                  value={formData.subject ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, subject: event.target.value })
                  }
                  className={inputClass()}
                />
              </Field>
              <Field label="Body">
                <textarea
                  rows={4}
                  value={formData.body ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, body: event.target.value })
                  }
                  className={inputClass()}
                />
              </Field>
            </>
          ) : null}

          {action === "talent" ? (
            <p className="text-sm text-zinc-600">
              {detail.candidate_name} will be added to the talent pool with
              their consent (recorded at application time). Existing talent pool
              entries are checked to avoid duplicates.
            </p>
          ) : null}

          {action === "process" ? (
            <p className="text-sm text-zinc-600">
              Extract structured data from the uploaded CV. This prepares the
              application for AI screening.
            </p>
          ) : null}

          {action === "screen" ? (
            <p className="text-sm text-zinc-600">
              Run AI screening to match the candidate profile against job
              requirements. The result is a draft recommendation — the final
              decision stays with HR.
            </p>
          ) : null}

          {action === "process" || action === "screen" ? (
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setAction(null)}>
                Cancel
              </Button>
              <Button onClick={runAction} loading={busy}>
                {action === "process" ? "Process CV" : "Run screening"}
              </Button>
            </div>
          ) : (
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setAction(null)}>
                Cancel
              </Button>
              <Button onClick={runAction} loading={busy}>
                Confirm
              </Button>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}