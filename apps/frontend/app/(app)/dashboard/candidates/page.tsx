"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import RecommendationBadge from "@/app/hr/_components/RecommendationBadge";
import { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { TableSkeleton } from "@/app/hr/_components/Skeleton";
import { inputClass } from "@/app/hr/_components/Field";
import {
  formatDate,
  formatStatus,
  getApplicationDetails,
  getRankedApplications,
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
  const [view, setView] = useState<"all" | "ranked">("ranked");

  useEffect(() => {
    (async () => {
      try {
        const [details, ranking] = await Promise.all([
          getApplicationDetails(),
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

  return (
    <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
          Candidates
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Review applications, screening results and take action.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg border border-zinc-200 bg-white p-0.5">
          <button
            type="button"
            onClick={() => setView("ranked")}
            className={`px-3 py-1.5 text-sm font-medium transition ${
              view === "ranked"
                ? "bg-violet-600 text-white"
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
                ? "bg-violet-600 text-white"
                : "text-zinc-600 hover:text-zinc-900"
            }`}
          >
            All applications
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
        ) : (
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
        )}
        <span className="text-sm tabular-nums text-zinc-500">
          {view === "ranked"
            ? `${ranked.length} ranked · ${leaderboardLabel}`
            : `${visible.length} of ${apps.length}`}
        </span>
      </div>

      {view === "ranked" ? (
        ranked.length === 0 ? (
          <EmptyState
            title="No evaluated candidates for this job"
            description="As candidates apply, the AI scores their CV against the job and the best ones appear here."
          />
        ) : (
          <div className="flex flex-col">
            {ranked.map((row, index) => {
              const detail = apps.find((a) => a.id === row.id);
              return (
                <div
                  key={row.id}
                  className={`flex items-center gap-4 border border-zinc-200 bg-white p-4 shadow-sm ${
                    index + 1 === 1 ? "border-l-4 border-l-violet-600" : ""
                  }`}
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-100 text-sm font-bold text-violet-700">
                    #{index + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-zinc-900">
                        {row.candidate_name ?? row.application_id}
                      </p>
                      <Badge status={row.status} />
                      {row.auto_rejected ? (
                        <span className="px-2 py-0.5 text-[11px] font-semibold text-rose-700 ring-1 ring-inset ring-rose-200 bg-rose-50">
                          AI auto-rejected
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
                          <span className="text-zinc-500">AI score</span>
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
                        className="font-medium text-violet-600 hover:underline"
                      >
                        Review →
                      </Link>
                    </div>
                  ) : (
                    <Link
                      href={`/dashboard/candidates/${detail?.id ?? row.id}`}
                      className="shrink-0 font-medium text-violet-600 hover:underline"
                    >
                      Review →
                    </Link>
                  )}
                </div>
              );
            })}
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
            <thead className="bg-violet-50/60 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-5 py-3">Candidate</th>
                <th className="px-5 py-3">Position</th>
                <th className="px-5 py-3">AI result</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Applied</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {visible.map((app) => (
                <tr key={app.id} className="transition hover:bg-violet-50/50">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center bg-violet-100 text-xs font-semibold text-violet-700">
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
                    <Link
                      href={`/dashboard/candidates/${app.id}`}
                      className="font-medium text-violet-600 hover:underline"
                    >
                      Review →
                    </Link>
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