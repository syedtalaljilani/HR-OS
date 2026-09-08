"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import Badge from "@/app/hr/_components/Badge";
import Button from "@/app/hr/_components/Button";
import CvPreview from "@/app/hr/_components/CvPreview";
import RecommendationBadge from "@/app/hr/_components/RecommendationBadge";
import RequirementItem from "@/app/hr/_components/RequirementItem";
import { Field, inputClass } from "@/app/hr/_components/Field";
import Modal, { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { DetailSkeleton } from "@/app/hr/_components/Skeleton";
import {
  api,
  formatDate,
  formatMoney,
  formatStatus,
  type ApplicationDetail,
  type Candidate,
  type CVDocument,
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

type ModalAction =
  | "status"
  | "decision"
  | "override"
  | "talent"
  | "email"
  | null;

type Tab = "overview" | "cv" | "screening" | "activity";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "cv", label: "CV" },
  { key: "screening", label: "AI screening" },
  { key: "activity", label: "Activity" },
];

function FieldRow({ label, value }: { label: string; value?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-6 border-b border-zinc-100 py-3 last:border-b-0">
      <dt className="text-sm text-zinc-500">{label}</dt>
      <dd className="text-right text-sm font-medium text-zinc-900">
        {value ?? "—"}
      </dd>
    </div>
  );
}

function EducationEntry({ entry }: { entry: unknown }) {
  if (typeof entry === "string") return <>{entry}</>;
  const e = entry as Record<string, unknown>;
  const parts = [e.degree, e.institution, e.years].filter(Boolean);
  return <>{parts.join(" · ")}</>;
}

function ExperienceEntry({ entry }: { entry: unknown }) {
  if (typeof entry === "string") return <>{entry}</>;
  const e = entry as Record<string, unknown>;
  const heading = [e.position, e.company, e.years].filter(Boolean).join(" · ");
  return (
    <div>
      <p className="font-medium text-zinc-900">{heading}</p>
      {e.description ? (
        <p className="mt-0.5 text-zinc-500">{String(e.description)}</p>
      ) : null}
    </div>
  );
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [action, setAction] = useState<ModalAction>(null);
  const [busy, setBusy] = useState(false);
  const [running, setRunning] = useState<"process" | "screen" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [previewCv, setPreviewCv] = useState<CVDocument | null>(null);

  const load = useCallback(async () => {
    try {
      const next = await api<ApplicationDetail>(`/applications/${id}`);
      setDetail(next);
      setError(null);
      if (next.candidate_id) {
        api<Candidate>(`/candidates/${next.candidate_id}`)
          .then(setCandidate)
          .catch(() => setCandidate(null));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load application");
    }
  }, [id]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  function openAction(next: ModalAction) {
    setFormData({});
    setAction(next);
  }

  async function runDirect(kind: "process" | "screen") {
    if (!detail) return;
    setRunning(kind);
    setError(null);
    try {
      if (kind === "process") {
        await api(`/applications/${detail.id}/process`, { method: "POST" });
      } else {
        await api(`/applications/${detail.id}/screen`, { method: "POST" });
      }
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : kind === "process"
            ? "CV processing could not be completed."
            : "AI screening could not be completed."
      );
    } finally {
      setRunning(null);
    }
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
      }
      setAction(null);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorNote message={error} />
        <Link
          href="/dashboard/candidates"
          className="mt-3 inline-block text-sm text-violet-600 hover:underline"
        >
          ← Back to candidates
        </Link>
      </div>
    );
  }
  if (!detail) return <DetailSkeleton />;

  const screening = detail.screening;
  const profile = candidate?.profile_data as
    | {
        skills?: string[];
        experience?: unknown[];
        education?: unknown[];
        address?: string | null;
      }
    | null
    | undefined;
  const profileSkills = Array.isArray(profile?.skills) ? profile.skills : [];
  const profileExperience = Array.isArray(profile?.experience)
    ? profile.experience
    : [];
  const profileEducation = Array.isArray(profile?.education)
    ? profile.education
    : [];

  const evidence =
    (screening?.evidence as { items?: EvidenceItem[] } | null)?.items ?? [];
  const missing =
    (screening?.missing_requirements as { items?: EvidenceItem[] } | null)?.items ?? [];
  const uncertain =
    (screening?.uncertainty as { items?: EvidenceItem[] } | null)?.items ?? [];

  const score =
    screening && screening.score !== null
      ? Math.round(Number(screening.score))
      : null;

  return (
    <div className="flex flex-1 flex-col gap-5 p-6 sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/dashboard/candidates"
            className="text-sm text-zinc-500 hover:text-zinc-800"
          >
            ← Candidates
          </Link>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-zinc-900">
            {detail.candidate_name}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            {detail.job_title ?? "Position"} • {detail.application_id}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge status={detail.status} />
          <Button
            variant="secondary"
            loading={running === "process"}
            onClick={() => runDirect("process")}
            className="text-[13px]"
          >
            Process CV
          </Button>
          <Button
            variant="secondary"
            loading={running === "screen"}
            onClick={() => runDirect("screen")}
            className="text-[13px]"
          >
            Run AI screening
          </Button>
        </div>
      </div>

      {notice ? (
        <p className="border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </p>
      ) : null}

      <div className="flex gap-1 border-b border-zinc-200" role="tablist">
        {TABS.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={tab === item.key}
            onClick={() => setTab(item.key)}
            className={`border-b-2 px-3 py-2 text-sm font-medium transition ${
              tab === item.key
                ? "border-violet-600 text-violet-700"
                : "border-transparent text-zinc-500 hover:text-zinc-800"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="border border-zinc-200 bg-white p-6 shadow-sm">
            <h2 className="mb-2 text-base font-semibold text-zinc-900">
              Candidate
            </h2>
            <dl>
              <FieldRow label="Full name" value={detail.candidate_name} />
              <FieldRow label="Email" value={detail.candidate_email} />
              <FieldRow label="Phone" value={detail.candidate_phone} />
              <FieldRow
                label="Address"
                value={
                  (candidate?.profile_data?.address as string | null | undefined) ?? null
                }
              />
              <FieldRow
                label="Expected salary"
                value={
                  detail.expected_salary
                    ? formatMoney(detail.expected_salary)
                    : null
                }
              />
            </dl>
            <dl className="mt-4 border-t border-zinc-200 pt-2">
              <FieldRow label="Position" value={detail.job_title} />
              <FieldRow label="Applied" value={formatDate(detail.created_at)} />
              <FieldRow label="Consent" value={detail.consent ? "On file" : "Not given"} />
            </dl>
          </section>

          <section className="border border-zinc-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-base font-semibold text-zinc-900">
              Extracted profile
            </h2>
            {profileSkills.length === 0 &&
            profileExperience.length === 0 &&
            profileEducation.length === 0 ? (
              <p className="text-sm text-zinc-500">
                No extracted profile yet.
                {running !== "process" ? (
                  <>
                    {" "}
                    Run{" "}
                    <button
                      onClick={() => runDirect("process")}
                      className="font-medium text-violet-600 hover:underline"
                    >
                      Process CV
                    </button>{" "}
                    to extract structured data.
                  </>
                ) : null}
              </p>
            ) : (
              <div className="flex flex-col gap-4">
                {profileSkills.length > 0 ? (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                      Skills
                    </h3>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {profileSkills.map((skill) => (
                        <span
                          key={skill}
                          className="bg-violet-50 px-2 py-0.5 text-sm text-violet-700"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
                {profileExperience.length > 0 ? (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                      Experience
                    </h3>
                    <ul className="mt-2 flex flex-col gap-3">
                      {profileExperience.map((entry, index) => (
                        <li key={index} className="text-sm text-zinc-700">
                          <ExperienceEntry entry={entry} />
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {profileEducation.length > 0 ? (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                      Education
                    </h3>
                    <ul className="mt-2 flex flex-col gap-1.5">
                      {profileEducation.map((entry, index) => (
                        <li key={index} className="text-sm text-zinc-700">
                          <EducationEntry entry={entry} />
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </div>
      ) : null}

      {tab === "cv" ? (
        <section className="border border-zinc-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-zinc-900">
            CV documents
          </h2>
          {detail.cv_documents.length === 0 ? (
            <EmptyState
              title="No CV uploaded"
              description="The candidate applied without uploading a CV."
            />
          ) : (
            <ul className="flex flex-col gap-2">
              {detail.cv_documents.map((doc) => (
                <li
                  key={doc.id}
                  className="flex items-center justify-between gap-3 border border-zinc-200 px-4 py-3"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center bg-violet-600 text-white">
                      <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                      </svg>
                    </span>
                  <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-zinc-900">
                        {doc.file_name}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {doc.mime_type ?? "Unknown type"} • uploaded{" "}
                        {formatDate(doc.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      variant="secondary"
                      className="text-[13px]"
                      onClick={() => setPreviewCv(doc)}
                    >
                      Preview
                    </Button>
                    <Badge status={doc.extraction_status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {tab === "screening" ? (
        <div className="flex flex-col gap-6">
          {!screening ? (
            <div className="border border-zinc-200 bg-white p-6 shadow-sm">
              <h2 className="text-base font-semibold text-zinc-900">
                AI screening
              </h2>
              <EmptyState
                title="No screening result yet"
                description="Run AI screening to match the candidate against the job requirements. The result is a draft recommendation — the final decision stays with HR."
              >
                <div className="flex flex-wrap gap-2">
                  <Button
                    loading={running === "screen"}
                    onClick={() => runDirect("screen")}
                  >
                    Run AI screening
                  </Button>
                  <Button
                    variant="secondary"
                    loading={running === "process"}
                    onClick={() => runDirect("process")}
                  >
                    Process CV first
                  </Button>
                </div>
              </EmptyState>
            </div>
          ) : (
            <>
              <section className="border border-zinc-200 border-l-4 border-l-violet-500 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold text-zinc-900">
                      AI recommendation
                    </h2>
                    <p className="mt-0.5 text-xs text-zinc-400">
                      Draft evaluation by the screening model — for HR
                      consideration.
                    </p>
                  </div>
                  <RecommendationBadge
                    recommendation={screening.recommendation}
                  />
                </div>

                <div className="mt-5 grid gap-6 sm:grid-cols-3">
                  <div>
                    <p className="text-xs text-zinc-500">Match score</p>
                    <p className="mt-1 text-3xl font-bold tracking-tight text-zinc-900">
                      {score ?? "–"}
                      <span className="text-base font-medium text-zinc-400">
                        /100
                      </span>
                    </p>
                    {score !== null ? (
                      <div className="mt-2 h-1.5 w-full bg-zinc-100">
                        <div
                          className="h-1.5 bg-violet-600"
                          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                        />
                      </div>
                    ) : null}
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Model</p>
                    <p className="mt-1 break-all font-mono text-sm text-zinc-700">
                      {screening.model ?? "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Human review</p>
                    <p className="mt-1 text-sm text-zinc-700">
                      {formatStatus(screening.hr_decision)}
                    </p>
                    {screening.reviewed_by ? (
                      <p className="text-xs text-zinc-400">
                        reviewed by {screening.reviewed_by.slice(0, 8)}…
                      </p>
                    ) : null}
                  </div>
                </div>
              </section>

              {(evidence.length > 0 ||
                missing.length > 0 ||
                uncertain.length > 0) ? (
                <section className="flex flex-col gap-6">
                  {evidence.length > 0 ? (
                    <RequirementGroup title="Requirement match" items={evidence} />
                  ) : null}
                  {missing.length > 0 ? (
                    <RequirementGroup title="Missing" items={missing} />
                  ) : null}
                  {uncertain.length > 0 ? (
                    <RequirementGroup title="Needs verification" items={uncertain} />
                  ) : null}
                </section>
              ) : (
                <p className="text-sm text-zinc-500">
                  No requirement evidence available yet.
                </p>
              )}
            </>
          )}

          <section className="border border-zinc-200 border-l-4 border-l-amber-400 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-zinc-900">
                  HR review
                </h2>
                <p className="mt-0.5 text-xs text-zinc-400">
                  The AI recommendation is not a decision — final outcomes are
                  set by HR here.
                </p>
              </div>
              {screening ? (
                <span className="px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ring-zinc-300 bg-white text-zinc-600">
                  {screening.hr_decision === "PENDING"
                    ? "HR decision pending"
                    : formatStatus(screening.hr_decision)}
                </span>
              ) : (
                <span className="px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ring-zinc-300 bg-white text-zinc-600">
                  Not screened yet
                </span>
              )}
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => openAction("decision")}>
                Final decision
              </Button>
              <Button variant="secondary" onClick={() => openAction("status")}>
                Change status
              </Button>
              <Button
                variant="secondary"
                onClick={() => openAction("override")}
                disabled={!screening}
              >
                Override recommendation
              </Button>
              <Button variant="secondary" onClick={() => openAction("talent")}>
                Add to talent pool
              </Button>
              <Button variant="secondary" onClick={() => openAction("email")}>
                Send email
              </Button>
            </div>
          </section>
        </div>
      ) : null}

      {tab === "activity" ? (
        <section className="border border-zinc-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-zinc-900">
            Status history
          </h2>
          {detail.status_history.length === 0 ? (
            <EmptyState title="No history yet" />
          ) : (
            <ol className="flex flex-col">
              {detail.status_history.map((entry, index) => (
                <li key={entry.id} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <span
                      className={`mt-1 h-2.5 w-2.5 ${
                        index === detail.status_history.length - 1
                          ? "bg-violet-600"
                          : "bg-emerald-500"
                      }`}
                    />
                    {index < detail.status_history.length - 1 ? (
                      <span className="w-px flex-1 bg-zinc-200" />
                    ) : null}
                  </div>
                  <div className="flex-1 pb-5">
                    <p className="text-sm font-medium text-zinc-900">
                      {entry.from_status
                        ? `${formatStatus(entry.from_status)} → ${formatStatus(entry.to_status)}`
                        : formatStatus(entry.to_status)}
                    </p>
                    <p className="mt-0.5 text-xs text-zinc-500">
                      {formatDate(entry.created_at)}
                      {entry.reason ? ` — ${entry.reason}` : ""}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      ) : null}

      <Modal
        open={action !== null}
        onClose={() => setAction(null)}
        title={
          action === "status"
            ? "Change status"
            : action === "decision"
              ? "Final decision"
              : action === "override"
                ? "Override recommendation"
                : action === "talent"
                  ? "Add to talent pool"
                  : "Send email"
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
                      {formatStatus(rec)}
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

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setAction(null)}>
              Cancel
            </Button>
            <Button onClick={runAction} loading={busy}>
              Confirm
            </Button>
          </div>
        </div>
      </Modal>

      <CvPreview
        open={previewCv !== null}
        onClose={() => setPreviewCv(null)}
        cvId={previewCv?.id ?? null}
        fileName={previewCv?.file_name ?? ""}
        mimeType={previewCv?.mime_type ?? null}
      />
    </div>
  );
}

function RequirementGroup({
  title,
  items,
}: {
  title: string;
  items: EvidenceItem[];
}) {
  return (
    <div>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h3>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <RequirementItem key={item.requirement} item={item} />
        ))}
      </div>
    </div>
  );
}