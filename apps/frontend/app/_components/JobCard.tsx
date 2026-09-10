import Link from "next/link";

import { formatSalary, type Job } from "@/app/_lib/api";

export default function JobCard({ job }: { job: Job }) {
  const salary = formatSalary(job.salary_min, job.salary_max);

  return (
    <Link
      href={`/jobs/${job.id}`}
      className="group flex w-full items-center justify-between gap-4 border-b border-zinc-200 bg-white px-5 py-4 transition last:border-b-0 hover:bg-navy-50/60"
    >
      <div className="min-w-0">
        <h3 className="text-base font-semibold text-zinc-900 group-hover:text-navy-700">
          {job.title}
        </h3>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-zinc-500">
          {job.location ? <span>{job.location}</span> : null}
          {job.location && salary ? (
            <span aria-hidden="true">•</span>
          ) : null}
          {salary ? <span>{salary}</span> : null}
        </div>
        {job.description ? (
          <p className="mt-1 line-clamp-1 text-sm text-zinc-600">
            {job.description}
          </p>
        ) : null}
      </div>
      <span className="shrink-0 border border-navy-200 bg-white px-3.5 py-1.5 text-sm font-medium text-navy-700 transition group-hover:bg-navy-600 group-hover:text-white">
        View position →
      </span>
    </Link>
  );
}