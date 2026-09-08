"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { LoadingScreen } from "@/app/hr/_components/Button";
import { inputClass } from "@/app/hr/_components/Field";
import {
  api,
  formatDate,
  formatStatus,
  type ApplicationSummary,
  type Candidate,
  type Job,
} from "@/app/hr/_lib/api";

export default function CandidatesPage() {
  const [apps, setApps] = useState<ApplicationSummary[] | null>(null);
  const [candidates, setCandidates] = useState<Record<string, Candidate>>({});
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [appList, candidateList, jobList] = await Promise.all([
          api<ApplicationSummary[]>("/applications"),
          api<Candidate[]>("/candidates"),
          api<Job[]>("/jobs"),
        ]);
        setApps(appList);
        setCandidates(
          Object.fromEntries(candidateList.map((c) => [c.id, c]))
        );
        setJobs(Object.fromEntries(jobList.map((j) => [j.id, j])));
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Failed to load applications"
        );
      }
    })();
  }, []);

  if (error) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (!apps) return <LoadingScreen />;

  const statuses = Array.from(new Set(apps.map((app) => app.status))).sort();
  const visible = filter
    ? apps.filter((app) => app.status === filter)
    : apps;

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Candidates</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Review applications, screening results and take action.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          className={`${inputClass()} w-56`}
        >
          <option value="">All statuses</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {formatStatus(status)}
            </option>
          ))}
        </select>
        <span className="text-sm text-zinc-500">{visible.length} total</span>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          title={filter ? "No applications in this status" : "No applications yet"}
          description="Applications submitted by candidates will appear here."
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-zinc-200 text-sm">
            <thead className="bg-zinc-50 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-5 py-3">Candidate</th>
                <th className="px-5 py-3">Position</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Received</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {visible.map((app) => {
                const candidate = candidates[app.candidate_id];
                const job = jobs[app.job_id];
                return (
                  <tr key={app.id} className="transition hover:bg-zinc-50">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-700">
                          {(candidate?.full_name ?? "?")
                            .split(" ")
                            .map((part) => part[0])
                            .slice(0, 2)
                            .join("")
                            .toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-zinc-900">
                            {candidate?.full_name ?? app.application_id}
                          </p>
                          <p className="text-xs text-zinc-500">
                            {app.application_id}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-zinc-600">
                      {job?.title ?? "—"}
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
                        className="font-medium text-indigo-600 hover:underline"
                      >
                        Review →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}