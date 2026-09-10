"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import RecommendationBadge from "@/app/hr/_components/RecommendationBadge";
import { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { TableSkeleton } from "@/app/hr/_components/Skeleton";
import { inputClass } from "@/app/hr/_components/Field";
import {
  formatDate,
  formatStatus,
  getApplicationDetails,
  getDeletedApplications,
  getRankedApplications,
  recoverApplication,
  deleteApplication,
  type ApplicationDetail,
  type RankedApplication,
} from "@/app/hr/_lib/api";

export default function CandidatesPage() {
  const [apps, setApps] = useState<ApplicationDetail[] | null>(null);
  const [ranked, setRanked] = useState<RankedApplication[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [jobFilter, setJobFilter] = useState("");
  const [view, setView] = useState<"ranked" | "all" | "deleted">("ranked");
  const [deletedApps, setDeletedApps] = useState<ApplicationDetail[] | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [details, ranking] = await Promise.all([
          getApplicationDetails(40),
          getRankedApplications(jobFilter || undefined, 10),
        ]);
        setApps(details);
        setRanked(ranking);
        if (!jobFilter && details.length > 0) {
          const ordered = Array.from(
            new Map(
              details.map((app) => [app.job_id, app.job_title ?? "—"])
            ).entries()
          ).sort((a, b) => a[1].localeCompare(b[1]));
          setJobFilter(ordered[0][0]);
        }
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Failed to load applications"
        );
      }
    })();
  }, [jobFilter]);

  const refresh = useCallback(async () => {
    const rankedApps = await getRankedApplications(jobFilter || undefined, 10);
    setRanked(rankedApps);
    const details = await getApplicationDetails(40);
    setApps(details);
  }, [jobFilter]);

  useEffect(() => {
    const timer = setInterval(() => {
      void refresh().catch(() => {
        // transient — keep last known data on screen
      });
    }, 8000);
    return () => clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (view !== "deleted") return;
    let cancelled = false;
    (async () => {
      try {
        const deleted = await getDeletedApplications();
        if (!cancelled) setDeletedApps(deleted);
      } catch {
        // keep last known trash state
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [view]);

  async function handleDelete(app: ApplicationDetail) {
    if (!window.confirm(`Delete application ${app.application_id} (${app.candidate_name ?? "candidate"})? The candidate will also be removed from the talent pool. Everything stays in the trash and can be recovered.`)) return;
    setBusyId(app.id);
    try {
      await deleteApplication(app.id);
      const [details, deleted] = await Promise.all([
        getApplicationDetails(40),
        getDeletedApplications(),
      ]);
      setApps(details);
      setDeletedApps(deleted);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRecover(app: ApplicationDetail) {
    setBusyId(app.id);
    try {
      await recoverApplication(app.id);
      const [details, deleted] = await Promise.all([
        getApplicationDetails(40),
        getDeletedApplications(),
      ]);
      setApps(details);
      setDeletedApps(deleted);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Recovery failed");
    } finally {
      setBusyId(null);
    }
  }

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (!apps || !ranked) {
    return (
      <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
        <div>
          <div className="skeleton h-6 w-40" />
          <div className="skeleton mt-2 h-3.5 w-72" />
        </div>
        <div className="skeleton h-9 w-full max-w-md" />
        <TableSkeleton rows={6} columns={5} />
      </div>
    );
  }

  const statuses = Array.from(new Set(apps.map((app) => app.status))).sort();

  const jobOptions = Array.from(
    new Map(apps.map((app) => [app.job_id, app.job_title ?? "—"])).entries()
  )
    .map(([id, title]) => ({ id, title }))
    .sort((a, b) => a.title.localeCompare(b.title));
  const selectedJob = jobOptions.find((job) => job.id === jobFilter);
  const leaderboardLabel = selectedJob
    ? `${selectedJob.title} leaderboard`
    : "No job selected";

  const visible = apps.filter((app) => {
    if (filter && app.status !== filter) return false;
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (
      (app.candidate_name ?? "").toLowerCase().includes(q) ||
      (app.job_title ?? "").toLowerCase().includes(q) ||
      app.application_id.toLowerCase().includes(q)
    );
  });

  const rankedQuery = query.trim().toLowerCase();
  const visibleRanked = ranked.filter((row) => {
    if (!rankedQuery) return true;
    return (
      (row.candidate_name ?? "").toLowerCase().includes(rankedQuery) ||
      (row.job_title ?? "").toLowerCase().includes(rankedQuery) ||
      row.application_id.toLowerCase().includes(rankedQuery)
    );
  });

  return (
    <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
          Candidates
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Review applications, screening results and take action.
        </p>
        <p className="mt-1 text-xs text-zinc-400">
          Showing candidates with a score of 40 or above — anything below is
          auto-rejected.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg border border-zinc-200 bg-white p-0.5">
          <button
            type="button"
            onClick={() => setView("ranked")}
            className={`px-3 py-1.5 text-sm font-medium transition ${
              view === "ranked"
                ? "bg-navy-600 text-white"
                : "text-zinc-600 hover:text-zinc-900"
            }`}
          >
            Top candidates
          </button>
          <button
            type="button"
            onClick={() => setView("all")}
            className={`px-3 py-1.5 text-sm font-medium transition ${
              view === "all"
                ? "bg-navy-600 text-white"
                : "text-zinc-600 hover:text-zinc-900"
            }`}
          >
            All applications
          </button>
          <button
            type="button"
            onClick={() => setView("deleted")}
            className={`px-3 py-1.5 text-sm font-medium transition ${
              view === "deleted"
                ? "bg-navy-600 text-white"
                : "text-zinc-600 hover:text-zinc-900"
            }`}
          >
            Deleted ({deletedApps ? deletedApps.length : "…"})
          </button>
        </div>
        <div className="relative min-w-0 flex-1 sm:max-w-sm">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={
              view === "ranked"
                ? "Search ranked candidates"
                : "Search candidates, positions or IDs"
            }
            aria-label="Search candidates"
            className={`${inputClass()} pl-9`}
          />
        </div>
        {view === "ranked" ? (
          <select
            value={jobFilter}
            onChange={(event) => setJobFilter(event.target.value)}
            aria-label="Leaderboard per job"
            className={`${inputClass()} w-auto min-w-48`}
          >
            {jobOptions.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </select>
        ) : view === "all" ? (
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            aria-label="Filter by status"
            className={`${inputClass()} w-auto min-w-40`}
          >
            <option value="">All statuses</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {formatStatus(status)}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-sm text-zinc-500">
            Deleted applications are hidden from every list until recovered.
          </span>
        )}
        <span className="text-sm tabular-nums text-zinc-500">
          {view === "ranked"
            ? rankedQuery
              ? `${visibleRanked.length} of ${ranked.length} ranked · ${leaderboardLabel}`
              : `${ranked.length} ranked · ${leaderboardLabel}`
            : view === "deleted"
              ? `${deletedApps?.length ?? 0} in trash`
              : `${visible.length} of ${apps.length}`}
        </span>
      </div>

      {view === "ranked" ? (
        ranked.length === 0 ? (
          <EmptyState
            title="No evaluated candidates for this job"
            description="As candidates apply, they are scored against the job and the best matches appear here."
          />
        ) : visibleRanked.length === 0 ? (
          <EmptyState
            title="No matching candidates"
            description="Try a different name, position or application ID."
          />
        ) : (
          <div className="flex flex-col">
            {visibleRanked.map((row, index) => {
              const detail = apps.find((a) => a.id === row.id);
              return (
                <div
                  key={row.id}
                  className={`flex items-center gap-4 border border-zinc-200 bg-white p-4 shadow-sm ${
                    index + 1 === 1 ? "border-l-4 border-l-navy-600" : ""
                  }`}
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-navy-100 text-sm font-bold text-navy-700">
                    #{ranked.indexOf(row) + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-zinc-900">
                        {row.candidate_name ?? row.application_id}
                      </p>
                      <Badge status={row.status} />
                      {row.auto_rejected ? (
                        <span className="px-2 py-0.5 text-[11px] font-semibold text-rose-700 ring-1 ring-inset ring-rose-200 bg-rose-50">
                          Auto-rejected
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-xs text-zinc-500">
                      {row.job_title ?? "—"} • {row.application_id}
                    </p>
                  </div>
                  {row.score !== null ? (
                    <div className="flex shrink-0 items-center gap-3">
                      <div className="w-24">
                        <div className="flex justify-between text-xs">
                          <span className="text-zinc-500">Score</span>
                          <span className="font-semibold tabular-nums text-zinc-900">
                            {Math.round(row.score)}
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 w-full bg-zinc-100">
                          <div
                            className={`h-1.5 ${
                              row.score >= 70
                                ? "bg-emerald-500"
                                : row.score >= 40
                                  ? "bg-amber-400"
                                  : "bg-rose-500"
                            }`}
                            style={{
                              width: `${Math.min(100, Math.max(0, row.score))}%`,
                            }}
                          />
                        </div>
                      </div>
                      <Link
                        href={`/dashboard/candidates/${detail?.id ?? row.id}`}
                        className="font-medium text-navy-600 hover:underline"
                      >
                        Review →
                      </Link>
                    </div>
                  ) : (
                    <Link
                      href={`/dashboard/candidates/${detail?.id ?? row.id}`}
                      className="shrink-0 font-medium text-navy-600 hover:underline"
                    >
                      Review →
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        )
      ) : view === "deleted" ? (
        deletedApps === null ? (
          <TableSkeleton rows={4} columns={4} />
        ) : deletedApps.length === 0 ? (
          <EmptyState
            title="Trash is empty"
            description="Deleted applications and candidates will appear here so they can be recovered."
          />
        ) : (
          <div className="overflow-x-auto border border-zinc-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-zinc-200 text-sm">
              <thead className="bg-navy-50/60 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-5 py-3">Candidate</th>
                  <th className="px-5 py-3">Position</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Deleted</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {deletedApps.map((app) => (
                  <tr key={app.id} className="transition hover:bg-zinc-50">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center bg-zinc-100 text-xs font-semibold text-zinc-600">
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
                    <td className="px-5 py-3.5 text-zinc-600">
                      {app.job_title ?? "—"}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge status={app.status} />
                    </td>
                    <td className="px-5 py-3.5 text-zinc-500">
                      {app.deleted_at ? formatDate(app.deleted_at) : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        type="button"
                        disabled={busyId === app.id}
                        onClick={() => handleRecover(app)}
                        className="font-medium text-emerald-600 hover:underline disabled:opacity-50"
                      >
                        {busyId === app.id ? "Restoring…" : "Recover"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : visible.length === 0 ? (
        <EmptyState
          title={
            filter || query.trim()
              ? "No matching applications"
              : "No applications yet"
          }
          description="Applications submitted by candidates will appear here."
        />
      ) : (
        <div className="overflow-x-auto border border-zinc-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-zinc-200 text-sm">
            <thead className="bg-navy-50/60 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-5 py-3">Candidate</th>
                <th className="px-5 py-3">Position</th>
                <th className="px-5 py-3">Result</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Applied</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {visible.map((app) => (
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
                  <td className="px-5 py-3.5 text-zinc-600">
                    {app.job_title ?? "—"}
                  </td>
                  <td className="px-5 py-3.5">
                    {app.screening ? (
                      <RecommendationBadge
                        recommendation={app.screening.recommendation}
                      />
                    ) : (
                      <span className="text-xs text-zinc-400">Not screened</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge status={app.status} />
                  </td>
                  <td className="px-5 py-3.5 text-zinc-500">
                    {formatDate(app.created_at)}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <div className="flex items-center justify-end gap-3">
                      <Link
                        href={`/dashboard/candidates/${app.id}`}
                        className="font-medium text-navy-600 hover:underline"
                      >
                        Review →
                      </Link>
                      <button
                        type="button"
                        title="Move to trash (recoverable)"
                        aria-label={`Delete ${app.application_id}`}
                        disabled={busyId === app.id}
                        onClick={() => handleDelete(app)}
                        className="text-zinc-400 transition hover:text-rose-600 disabled:opacity-50"
                      >
                        <svg
                          className="h-4 w-4"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}