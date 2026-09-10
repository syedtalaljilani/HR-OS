"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import Badge from "@/app/hr/_components/Badge";
import Button from "@/app/hr/_components/Button";
import CvPreview from "@/app/hr/_components/CvPreview";
import RecommendationBadge from "@/app/hr/_components/RecommendationBadge";
import RequirementItem from "@/app/hr/_components/RequirementItem";
import { Field, inputClass } from "@/app/hr/_components/Field";
import Modal, { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { DetailSkeleton } from "@/app/hr/_components/Skeleton";
import { cleanAddressQuery } from "@/app/hr/_lib/address";
import {
  api,
  deleteApplication,
  deleteCandidate,
  draftEmailWithAI,
  formatDate,
  formatMoney,
  formatStatus,
  recoverApplication,
  scheduleInterview,
  type ApplicationDetail,
  type Candidate,
  type CVDocument,
  type EvidenceItem,
  type Interview,
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
  | "interview"
  | null;

type Tab = "overview" | "cv" | "screening" | "activity";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "cv", label: "CV" },
  { key: "screening", label: "Screening" },
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
  const router = useRouter();

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
  const [aiDrafting, setAiDrafting] = useState(false);
  const [companyLocation, setCompanyLocation] = useState("");

  const mapSearchUrl = (address: string) =>
    `https://www.google.com/maps/search/?api=1&q=${encodeURIComponent(cleanAddressQuery(address))}`;

  const mapEmbedUrl = (address: string) =>
    `https://maps.google.com/maps?q=${encodeURIComponent(cleanAddressQuery(address))}&z=15&output=embed`;

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
      api<{ company_location: string }>("/settings/organization")
        .then((settings) => setCompanyLocation(settings.company_location ?? ""))
        .catch(() => setCompanyLocation(""));
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

  useEffect(() => {
    if (!detail?.id) return;
    let cancelled = false;
    let seenBusy = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function tick() {
      try {
        const queue = await api<{ id: string; application_id: string; status: string }[]>(
          "/screening-queue?limit=50"
        );
        const busyEntry = queue.find(
          (item) =>
            item.application_id === detail!.id &&
            (item.status === "QUEUED" || item.status === "PROCESSING")
        );
        if (busyEntry && !cancelled) {
          seenBusy = true;
          await load(); // refresh candidate + screening as the worker progresses
          return;
        }
        if (seenBusy && !busyEntry && !cancelled) {
          await load(); // final refresh once the worker has finished
        }
        if (timer) clearInterval(timer);
      } catch {
        // transient hiccup — keep polling; stops once the queue is quiet
      }
    }

    timer = setInterval(tick, 8000);
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [detail, load]);

  function openAction(next: ModalAction) {
    const prefill: Record<string, string> = {};
    if (next === "interview" && detail && detail.interviews.length > 0) {
      const latest = detail.interviews[detail.interviews.length - 1];
      const saved = new Date(latest.scheduled_at);
      const pad = (n: number) => String(n).padStart(2, "0");
      prefill.type = latest.type;
      prefill.scheduledAt = [
        saved.getFullYear(),
        pad(saved.getMonth() + 1),
        pad(saved.getDate()),
      ].join("-") + `T${pad(saved.getHours())}:${pad(saved.getMinutes())}`;
      prefill.notes = latest.notes ?? "";
      const stored = latest.location;
      if (stored) {
        const lines = stored
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter(Boolean);
        const mapLine = lines.find((line) => /^map\s*:\s*\S+/i.test(line));
        const mapLink =
          mapLine?.match(/^map\s*:\s*(\S+)\s*$/i)?.[1] ?? "";
        const addressText = lines
          .filter((line) => !/^map\s*:\s*/i.test(line))
          .join(", ");
        if (mapLink) {
          prefill.locationMode = "custom";
          if (addressText) prefill.location = addressText;
          prefill.mapLink = mapLink;
        } else if (
          /^https?:\/\/\S+$/i.test(stored.trim()) &&
          !addressText
        ) {
          prefill.locationMode = "remote";
          prefill.location = stored.trim();
        } else {
          prefill.locationMode = "custom";
          prefill.location = addressText || stored.trim();
        }
      } else {
        prefill.locationMode = "onsite";
      }
    }
    setFormData(prefill);
    setAction(next);
  }

  async function runDirect(kind: "process" | "screen") {
    if (!detail) return;
    setRunning(kind);
    setError(null);
    try {
      let entryId: string | null = null;
      if (kind === "process") {
        const res = await api<{ entry_id: string }>(
          `/applications/${detail.id}/process`,
          { method: "POST" }
        );
        entryId = res.entry_id;
      } else {
        const res = await api<{ entry_id: string }>(
          `/applications/${detail.id}/screen`,
          { method: "POST" }
        );
        entryId = res.entry_id;
      }
      setNotice(
        kind === "process"
          ? "CV processing started in the background. It keeps running even if you leave this page."
          : "Screening started in the background. It keeps running even if you leave this page."
      );
      void pollUntilDone(kind, entryId);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : kind === "process"
            ? "CV processing could not be queued."
            : "Screening could not be queued."
      );
      setRunning(null);
    }
  }

  async function pollUntilDone(kind: "process" | "screen", entryId: string) {
    let attempts = 0;
    while (attempts < 90) {
      attempts += 1;
      await new Promise((resolve) => setTimeout(resolve, 8000));
      try {
        const queue = await api<{ id: string; status: string }[]>(
          "/screening-queue?limit=50"
        );
        const entry = queue.find((item) => item.id === entryId);
        if (entry && (entry.status === "COMPLETED" || entry.status === "FAILED")) {
          setRunning(null);
          setNotice(
            kind === "screen"
              ? "Screening finished — see the results below."
              : "CV processing finished."
          );
          await load();
          return;
        }
      } catch {
        // transient network/refresh hiccup — keep polling
      }
    }
    setRunning(null);
    setNotice(
      "Still running in the background — live progress is on the dashboard screening queue."
    );
  }

  async function handleDeleteApplication() {
    if (!detail) return;
    if (
      !window.confirm(
        `Move ${detail.application_id} (${detail.candidate_name ?? "candidate"}) to trash? The candidate will also be removed from the talent pool. Everything stays in the trash and can be recovered.`
      )
    )
      return;
    setBusy(true);
    try {
      await deleteApplication(detail.id);
      setNotice("Application and candidate moved to trash.");
      router.replace("/dashboard/candidates");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRecoverApplication() {
    if (!detail) return;
    setBusy(true);
    try {
      await recoverApplication(detail.id);
      setNotice("Application and candidate restored from trash.");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Recovery failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteCandidate() {
    if (!detail) return;
    if (
      !window.confirm(
        `Delete candidate ${detail.candidate_name} and ALL their applications? Everything is moved to trash and can be recovered later.`
      )
    )
      return;
    setBusy(true);
    try {
      await deleteCandidate(detail.candidate_id);
      setNotice("Candidate and all their applications moved to trash.");
      router.replace("/dashboard/candidates");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Delete failed");
    } finally {
      setBusy(false);
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
      } else if (action === "interview") {
        const when = formData.scheduledAt;
        if (!when) {
          setError("Pick a date and time for the interview call.");
          setBusy(false);
          return;
        }
        const mode = formData.locationMode ?? "onsite";
        let location: string | undefined;
        if (mode === "remote") {
          if (!formData.location?.trim()) {
            setError("Enter the meeting link for the remote interview.");
            setBusy(false);
            return;
          }
          location = formData.location || undefined;
        } else if (mode === "custom") {
          const address = formData.location?.trim() ?? "";
          const mapLink = formData.mapLink?.trim() ?? "";
          if (address && mapLink) location = `${address}\nMap: ${mapLink}`;
          else if (mapLink) location = `Map: ${mapLink}`;
          else location = address || undefined;
        }
        await scheduleInterview(detail.id, {
          type: (formData.type as "HR" | "TECHNICAL") ?? "HR",
          scheduled_at: new Date(when).toISOString(),
          location,
          notes: formData.notes || undefined,
        });
        setNotice("Interview call scheduled and the candidate has been emailed.");
      }
      setAction(null);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function aiEmailAssist() {
    if (!detail) return;
    setAiDrafting(true);
    setError(null);
    try {
      const draft = await draftEmailWithAI(detail.id, {
        email_type: formData.type || undefined,
        reason: formData.reason || undefined,
        hr_notes: formData.hrNotes || undefined,
        tone: formData.tone || undefined,
      });
      setFormData((prev) => ({
        ...prev,
        subject: draft.subject,
        body: draft.body,
      }));
      setNotice("Draft ready — review and edit before sending.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Draft could not be generated"
      );
    } finally {
      setAiDrafting(false);
    }
  }

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorNote message={error} />
        <Link
          href="/dashboard/candidates"
          className="mt-3 inline-block text-sm text-navy-600 hover:underline"
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

  const canInterview =
    screening !== null &&
    score !== null &&
    score >= 40 &&
    detail.status !== "REJECTED";

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
          {detail.deleted_at ? (
            <Button
              variant="secondary"
              loading={busy}
              onClick={() => void handleRecoverApplication()}
              className="text-[13px]"
            >
              Recover application
            </Button>
          ) : (
            <>
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
                Run screening
              </Button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleDeleteApplication()}
                title="Move application to trash (recoverable)"
                className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-[13px] font-medium text-zinc-500 transition hover:border-rose-200 hover:text-rose-600 disabled:opacity-50"
              >
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                </svg>
                Delete
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleDeleteCandidate()}
                title="Delete candidate and all their applications (recoverable)"
                className="text-[12px] font-medium text-zinc-400 transition hover:text-rose-600 disabled:opacity-50"
              >
                Delete candidate
              </button>
            </>
          )}
        </div>
      </div>

      {detail.deleted_at ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          This application was moved to trash on {formatDate(detail.deleted_at)}.
          It is hidden from all lists and can be restored with Recover application.
        </div>
      ) : null}

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
                ? "border-navy-600 text-navy-700"
                : "border-transparent text-zinc-500 hover:text-zinc-800"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <>
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
                      className="font-medium text-navy-600 hover:underline"
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
                          className="bg-navy-50 px-2 py-0.5 text-sm text-navy-700"
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

          <section className="border border-zinc-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-base font-semibold text-zinc-900">
              Interview calls
            </h2>
            {detail.interviews.length === 0 ? (
              <p className="text-sm text-zinc-500">
                No interview calls scheduled yet. Use &quot;Call for interview&quot; once
                the candidate clears human review (score 40+).
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {detail.interviews.map((interview: Interview) => (
                  <li
                    key={interview.id}
                    className="flex items-center justify-between gap-3 border border-zinc-200 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-zinc-900">
                        {interview.type === "TECHNICAL"
                          ? "Technical interview"
                          : "HR interview"}
                        {interview.location ? ` · ${interview.location}` : ""}
                      </p>
                      <p className="mt-0.5 text-xs text-zinc-500">
                        {formatDate(interview.scheduled_at)}
                      </p>
                      {interview.notes ? (
                        <p className="mt-1 text-xs text-zinc-500">
                          {interview.notes}
                        </p>
                      ) : null}
                    </div>
                    <Badge status={interview.status} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
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
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center bg-navy-600 text-white">
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
                Screening
              </h2>
              <EmptyState
                title="No screening result yet"
                description="Screening matches the candidate against the job requirements. The result is a draft recommendation — the final call stays with HR."
              >
                <div className="flex flex-wrap gap-2">
                  <Button
                    loading={running === "screen"}
                    onClick={() => runDirect("screen")}
                  >
                    Run screening
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
              <section className="border border-zinc-200 border-l-4 border-l-navy-500 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold text-zinc-900">
                      Recommendation
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
                          className="h-1.5 bg-navy-600"
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
                  The recommendation is not a decision — final outcomes are
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
              <Button
                onClick={() => openAction("interview")}
                disabled={!canInterview}
                title={
                  canInterview
                    ? "Schedule an interview call and email the candidate"
                    : "Needs a screening score of 40+ to move forward"
                }
              >
                Call for interview
              </Button>
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
                          ? "bg-navy-600"
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
                  : action === "interview"
                    ? "Schedule interview call"
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
              <Field label="New recommendation *">
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

              <div className="border border-navy-200 bg-navy-50/50 p-4">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center bg-navy-600 text-white">
                    <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
                    </svg>
                  </span>
                  <span className="text-sm font-semibold text-navy-700">
                    Writing assistant
                  </span>
                </div>
                <p className="mt-2 text-xs text-zinc-500">
                  Describe what you would like to say and pick a tone — a first draft
                  is written for you. Review and edit the subject and body below
                  before sending.
                </p>
                <div className="mt-3 flex flex-col gap-2">
                  <textarea
                    rows={2}
                    value={formData.hrNotes ?? ""}
                    onChange={(event) =>
                      setFormData({ ...formData, hrNotes: event.target.value })
                    }
                    className={inputClass("bg-white")}
                    placeholder="e.g. mention we went with a more senior profile"
                  />
                  <select
                    value={formData.tone ?? ""}
                    onChange={(event) =>
                      setFormData({ ...formData, tone: event.target.value })
                    }
                    className={`${inputClass("bg-white")} w-auto`}
                  >
                    <option value="">Tone — default</option>
                    <option value="warm">Warm</option>
                    <option value="firm">Firm / direct</option>
                    <option value="professional">Professional</option>
                  </select>
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={aiEmailAssist}
                      loading={aiDrafting}
                    >
                      Generate draft
                    </Button>
                  </div>
                </div>
              </div>

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

          {action === "interview" ? (
            <>
              <Field label="Interview type *">
                <select
                  value={formData.type ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, type: event.target.value })
                  }
                  className={inputClass()}
                >
                  <option value="HR">HR</option>
                  <option value="TECHNICAL">Technical</option>
                </select>
              </Field>
              <Field
                label="Date & time *"
                hint="Enter local time — it is shown in Pakistan time in the candidate email."
              >
                <input
                  type="datetime-local"
                  value={formData.scheduledAt ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, scheduledAt: event.target.value })
                  }
                  className={inputClass()}
                />
              </Field>
              <Field label="Where *">
                <select
                  value={formData.locationMode ?? "onsite"}
                  onChange={(event) =>
                    setFormData({
                      ...formData,
                      locationMode: event.target.value,
                    })
                  }
                  className={inputClass()}
                >
                  <option value="onsite">Onsite — company office</option>
                  <option value="remote">Remote — meeting link</option>
                  <option value="custom">Other — own address / map</option>
                </select>
              </Field>

              {formData.locationMode === "onsite" ? (
                companyLocation ? (
                  <div>
                    <p className="text-sm text-zinc-600">
                      {companyLocation}
                    </p>
                    <a
                      href={mapSearchUrl(companyLocation)}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-sm font-medium text-navy-600 hover:underline"
                    >
                      Open in Google Maps →
                    </a>
                    <iframe
                      src={mapEmbedUrl(companyLocation)}
                      title="Company location map"
                      loading="lazy"
                      className="mt-3 h-44 w-full border border-zinc-200"
                    />
                    <p className="mt-2 text-xs text-zinc-500">
                      The candidate email will include the company address with a
                      map link.
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-600">
                    No office location saved yet — add it under{" "}
                    <Link
                      href="/dashboard/settings"
                      className="font-medium text-navy-600 hover:underline"
                    >
                      Settings
                    </Link>{" "}
                    so the map is included.
                  </p>
                )
              ) : null}

              {formData.locationMode === "remote" ? (
                <Field label="Meeting link *">
                  <input
                    value={formData.location ?? ""}
                    onChange={(event) =>
                      setFormData({ ...formData, location: event.target.value })
                    }
                    className={inputClass()}
                    placeholder="e.g. Google Meet https://meet.example/abc"
                  />
                </Field>
              ) : null}

              {formData.locationMode === "custom" ? (
                <>
                  <Field label="Address / location">
                    <input
                      value={formData.location ?? ""}
                      onChange={(event) =>
                        setFormData({ ...formData, location: event.target.value })
                      }
                      className={inputClass()}
                      placeholder="e.g. Head office, 2nd floor, City Center"
                    />
                  </Field>
                  <Field
                    label="Map link (optional)"
                    hint="If set, a map link is included in the candidate email."
                  >
                    <input
                      value={formData.mapLink ?? ""}
                      onChange={(event) =>
                        setFormData({ ...formData, mapLink: event.target.value })
                      }
                      className={inputClass()}
                      placeholder="https://www.google.com/maps/search/?api=1&q=..."
                    />
                  </Field>
                </>
              ) : null}
              <Field label="Notes">
                <textarea
                  rows={3}
                  value={formData.notes ?? ""}
                  onChange={(event) =>
                    setFormData({ ...formData, notes: event.target.value })
                  }
                  className={inputClass()}
                  placeholder="e.g. 45 minutes, review the technical case study beforehand"
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