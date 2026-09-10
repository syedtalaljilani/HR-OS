"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import RecommendationBadge from "@/app/hr/_components/RecommendationBadge";
import { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import Kpi from "@/app/hr/_components/Kpi";
import { KpiSkeleton, TableSkeleton } from "@/app/hr/_components/Skeleton";
import {
  api,
  formatDate,
  getApplicationDetails,
  getScreeningQueue,
  getScreeningQueueStats,
  type ApplicationDetail,
  type Job,
  type TalentPoolEntry,
  type ScreeningQueueEntry,
  type ScreeningQueueStats,
} from "@/app/hr/_lib/api";

const REVIEW_STATUSES = ["PROCESSING", "HR_REVIEW"];

export default function DashboardPage() {
  const [details, setDetails] = useState<ApplicationDetail[] | null>(null);
  const [openJobs, setOpenJobs] = useState<number | null>(null);
  const [poolCount, setPoolCount] = useState<number | null>(null);
  const [queueEntries, setQueueEntries] = useState<ScreeningQueueEntry[] | null>(null);
  const [queueStats, setQueueStats] = useState<ScreeningQueueStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [apps, jobs, pool, queue, stats] = await Promise.all([
          getApplicationDetails(),
          api<Job[]>("/jobs"),
          api<TalentPoolEntry[]>("/talent-pool"),
          getScreeningQueue(undefined, 20),
          getScreeningQueueStats(),
        ]);
        setDetails(apps);
        setOpenJobs(jobs.filter((job) => job.status === "OPEN").length);
        setPoolCount(pool.length);
        setQueueEntries(queue);
        setQueueStats(stats);
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Failed to load dashboard"
        );
      }
    })();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      void (async () => {
        try {
          const [queue, stats, apps] = await Promise.all([
            getScreeningQueue(undefined, 20),
            getScreeningQueueStats(),
            getApplicationDetails(),
          ]);
          setQueueEntries(queue);
          setQueueStats(stats);
          setDetails(apps);
        } catch {
          // transient — keep the last known state on screen
        }
      })();
    }, 8000);
    return () => clearInterval(timer);
  }, []);

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (!details || openJobs === null || poolCount === null) {
    return (
      <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
        <div>
          <div className="skeleton h-6 w-48" />
          <div className="skeleton mt-2 h-3.5 w-72" />
        </div>
        <KpiSkeleton count={4} />
        <TableSkeleton rows={4} columns={5} />
      </div>
    );
  }

  const needsReview = details.filter((app) =>
    REVIEW_STATUSES.includes(app.status)
  );
  const recent = details.slice(0, 6);
  const activeQueue = queueEntries?.filter(
    (e) => e.status === "QUEUED" || e.status === "PROCESSING"
  ) ?? [];

  return (
    <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
          Overview
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Recruitment activity at a glance.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Kpi
          label="Open jobs"
          value={openJobs}
          tone="bg-emerald-50 text-emerald-600"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.1a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25v-4.1M16.5 6.75V4.5A2.25 2.25 0 0 0 14.25 2.25h-4.5A2.25 2.25 0 0 0 7.5 4.5v2.25m-4.5 0h18v6a3 3 0 0 1-3 3h-12a3 3 0 0 1-3-3v-6Z" />
            </svg>
          }
        />
        <Kpi
          label="Applications"
          value={details.length}
          tone="bg-navy-50 text-navy-600"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6V3m0 0h3m-3 0v3M12 3h-1.5a1.5 1.5 0 0 0-1.5 1.5v13.5a1.5 1.5 0 0 0 1.5 1.5h8.25a1.5 1.5 0 0 0 1.5-1.5V12M3 6.75h6M3 12h6M3 17.25h6" />
            </svg>
          }
        />
        <Kpi
          label="In review"
          value={needsReview.length}
          tone="bg-amber-50 text-amber-600"
          hint="Requires HR attention"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          }
        />
        <Kpi
          label="Screening queue"
          value={queueStats?.PROCESSING ?? 0}
          tone="bg-blue-50 text-blue-600"
          hint={`${queueStats?.QUEUED ?? 0} queued, ${queueStats?.FAILED ?? 0} failed`}
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" />
            </svg>
          }
        />
        <Kpi
          label="Talent pool"
          value={poolCount}
          tone="bg-navy-50 text-navy-600"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
          }
        />
      </div>

      {activeQueue.length > 0 ? (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-900">
              Auto-screening queue
            </h2>
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
              {activeQueue.length} active
            </span>
          </div>
          <QueueTable entries={activeQueue} />
        </section>
      ) : null}

      {needsReview.length > 0 ? (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-900">
              Needs review
            </h2>
            <Link
              href="/dashboard/candidates"
              className="text-sm font-medium text-navy-600 hover:text-navy-700"
            >
              View all →
            </Link>
          </div>
          <ReviewTable apps={needsReview} />
        </section>
      ) : null}

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">
            Recent applications
          </h2>
          <Link
            href="/dashboard/candidates"
            className="text-sm font-medium text-navy-600 hover:text-navy-700"
          >
            View all →
          </Link>
        </div>
        {recent.length === 0 ? (
          <EmptyState
            title="No applications yet"
            description="Applications will appear here once candidates start applying."
          >
            <Link
              href="/dashboard/jobs"
              className="inline-flex items-center bg-navy-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-navy-700"
            >
              View jobs
            </Link>
          </EmptyState>
        ) : (
          <ReviewTable apps={recent} />
        )}
      </section>
    </div>
  );
}

function ReviewTable({ apps }: { apps: ApplicationDetail[] }) {
  return (
    <div className="overflow-x-auto border border-zinc-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-zinc-200 text-sm">
        <thead className="bg-navy-50/60 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-5 py-3">Candidate</th>
            <th className="px-5 py-3">Position</th>
            <th className="px-5 py-3">Status</th>
            <th className="px-5 py-3">Result</th>
            <th className="px-5 py-3">Applied</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {apps.map((app) => (
            <tr key={app.id} className="transition hover:bg-navy-50/50">
              <td className="px-5 py-3.5">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center bg-navy-100 text-xs font-semibold text-navy-700">
                    {(app.candidate_name ?? "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()}
                  </span>
                  <div>
                    <p className="font-medium text-zinc-900">
                      {app.candidate_name ?? app.application_id}
                    </p>
                    <p className="text-xs text-zinc-400">{app.application_id}</p>
                  </div>
                </div>
              </td>
              <td className="px-5 py-3.5 text-zinc-600">{app.job_title ?? "—"}</td>
              <td className="px-5 py-3.5">
                <Badge status={app.status} />
              </td>
              <td className="px-5 py-3.5">
                {app.screening ? (
                  <RecommendationBadge recommendation={app.screening.recommendation} />
                ) : (
                  <span className="text-xs text-zinc-400">Not screened</span>
                )}
              </td>
              <td className="px-5 py-3.5 text-zinc-500">
                {formatDate(app.created_at)}
              </td>
              <td className="px-5 py-3.5 text-right">
                <Link
                  href={`/dashboard/candidates/${app.id}`}
                  className="font-medium text-navy-600 hover:underline"
                >
                  Review →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const QUEUE_STATUS_COLORS: Record<string, string> = {
  QUEUED: "bg-zinc-100 text-zinc-600 ring-zinc-300",
  PROCESSING: "bg-blue-50 text-blue-700 ring-blue-300",
  COMPLETED: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  FAILED: "bg-rose-50 text-rose-700 ring-rose-300",
};

function QueueTable({ entries }: { entries: ScreeningQueueEntry[] }) {
  return (
    <div className="overflow-x-auto border border-zinc-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-zinc-200 text-sm">
        <thead className="bg-blue-50/60 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-5 py-3">Candidate</th>
            <th className="px-5 py-3">Position</th>
            <th className="px-5 py-3">Action</th>
            <th className="px-5 py-3">Status</th>
            <th className="px-5 py-3">Score</th>
            <th className="px-5 py-3">Queued</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {entries.map((entry) => (
            <tr key={entry.id} className="transition hover:bg-blue-50/50">
              <td className="px-5 py-3.5">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center bg-blue-100 text-xs font-semibold text-blue-700">
                    {(entry.candidate_name ?? "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()}
                  </span>
                  <div>
                    <p className="font-medium text-zinc-900">
                      {entry.candidate_name ?? "Unknown"}
                    </p>
                  </div>
                </div>
              </td>
              <td className="px-5 py-3.5 text-zinc-600">{entry.job_title ?? "—"}</td>
              <td className="px-5 py-3.5">
                <div className="flex flex-col items-start gap-1">
                  <span className="text-xs font-medium text-zinc-700">
                    {entry.action}
                  </span>
                  <span className="text-[10px] uppercase tracking-wide text-zinc-400">
                    {entry.source}
                  </span>
                </div>
              </td>
              <td className="px-5 py-3.5">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${QUEUE_STATUS_COLORS[entry.status] ?? QUEUE_STATUS_COLORS.QUEUED}`}
                >
                  {entry.status === "PROCESSING" ? (
                    <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
                  ) : null}
                  {entry.status}
                </span>
              </td>
              <td className="px-5 py-3.5 text-zinc-600">
                {entry.score != null ? `${entry.score}/100` : "—"}
              </td>
              <td className="px-5 py-3.5 text-zinc-500">
                {formatDate(entry.queued_at)}
              </td>
              <td className="px-5 py-3.5 text-right">
                <Link
                  href={`/dashboard/candidates/${entry.application_id}`}
                  className="font-medium text-navy-600 hover:underline"
                >
                  View →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}