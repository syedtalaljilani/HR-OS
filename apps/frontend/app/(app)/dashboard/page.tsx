"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { LoadingScreen } from "@/app/hr/_components/Button";
import {
  api,
  formatDate,
  type ApplicationSummary,
  type Job,
  type TalentPoolEntry,
} from "@/app/hr/_lib/api";

type Overview = {
  openJobs: number;
  totalJobs: number;
  applications: ApplicationSummary[];
  candidateCount: number;
  poolCount: number;
  pipelineCount: number;
};

function StatCard({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  accent: string;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-500">{label}</span>
        <span
          className={`flex h-9 w-9 items-center justify-center rounded-xl ${accent}`}
        >
          {icon}
        </span>
      </div>
      <p className="mt-2 text-3xl font-bold text-zinc-900">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [jobs, applications, pool] = await Promise.all([
          api<Job[]>("/jobs"),
          api<ApplicationSummary[]>("/applications"),
          api<TalentPoolEntry[]>("/talent-pool"),
        ]);
        const candidateIds = new Set(
          applications.map((app) => app.candidate_id)
        );
        setData({
          openJobs: jobs.filter((job) => job.status === "OPEN").length,
          totalJobs: jobs.length,
          applications,
          candidateCount: candidateIds.size,
          poolCount: pool.length,
          pipelineCount: applications.filter((app) =>
            [
              "PROCESSING",
              "HR_REVIEW",
              "SHORTLISTED",
              "INTERVIEW_SCHEDULED",
              "TECHNICAL_INTERVIEW",
              "TECHNICAL_REVIEW",
              "BEHAVIORAL_INTERVIEW",
              "FINAL_REVIEW",
            ].includes(app.status)
          ).length,
        });
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Failed to load dashboard"
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
  if (!data) return <LoadingScreen />;

  const recent = data.applications.slice(0, 6);

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Overview</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Recruitment activity at a glance.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Open positions"
          value={data.openJobs}
          accent="bg-emerald-50 text-emerald-600"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
            </svg>
          }
        />
        <StatCard
          label="Total applications"
          value={data.applications.length}
          accent="bg-indigo-50 text-indigo-600"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          }
        />
        <StatCard
          label="Applications in pipeline"
          value={data.pipelineCount}
          accent="bg-violet-50 text-violet-600"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          }
        />
        <StatCard
          label="Unique candidates"
          value={data.candidateCount}
          accent="bg-amber-50 text-amber-600"
          icon={
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM3 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 9.374 21c-2.331 0-4.512-.645-6.374-1.766Z" />
            </svg>
          }
        />
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">
            Recent applications
          </h2>
          <Link
            href="/dashboard/candidates"
            className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            View all →
          </Link>
        </div>
        {recent.length === 0 ? (
          <EmptyState
            title="No applications yet"
            description="Applications will appear here once candidates start applying."
          />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-zinc-200 text-sm">
              <thead className="bg-zinc-50 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-5 py-3">Application</th>
                  <th className="px-5 py-3">Job</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Received</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {recent.map((app) => (
                  <tr
                    key={app.id}
                    className="transition hover:bg-zinc-50"
                  >
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/dashboard/candidates/${app.id}`}
                        className="font-medium text-indigo-600 hover:underline"
                      >
                        {app.application_id}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 text-zinc-600">{app.job_id}</td>
                    <td className="px-5 py-3.5">
                      <Badge status={app.status} />
                    </td>
                    <td className="px-5 py-3.5 text-zinc-500">
                      {formatDate(app.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}