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
  type ApplicationDetail,
} from "@/app/hr/_lib/api";

export default function CandidatesPage() {
  const [apps, setApps] = useState<ApplicationDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setApps(await getApplicationDetails());
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Failed to load applications"
        );
      }
    })();
  }, []);

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (!apps) {
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
            placeholder="Search candidates, positions or IDs"
            aria-label="Search candidates"
            className={`${inputClass()} pl-9`}
          />
        </div>
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
        <span className="text-sm tabular-nums text-zinc-500">
          {visible.length} of {apps.length}
        </span>
      </div>

      {visible.length === 0 ? (
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