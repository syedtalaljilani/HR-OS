import Link from "next/link";

import { formatSalary, type Job } from "@/app/_lib/api";

export default function JobCard({ job }: { job: Job }) {
  const salary = formatSalary(job.salary_min, job.salary_max);
  const skills = (
    (job.requirements as Record<string, unknown> | null)?.skills
  ) as string[] | undefined;

  return (
    <Link
      href={`/jobs/${job.id}`}
      className="group flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-6 transition hover:border-indigo-300 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-lg font-semibold text-zinc-900 group-hover:text-indigo-700">
          {job.title}
        </h2>
        {salary ? (
          <span className="whitespace-nowrap rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700">
            {salary}
          </span>
        ) : null}
      </div>
      {job.location ? (
        <p className="text-sm text-zinc-500">{job.location}</p>
      ) : null}
      {job.description ? (
        <p className="line-clamp-2 text-sm text-zinc-600">{job.description}</p>
      ) : null}
      {skills && skills.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1.5">
          {skills.slice(0, 6).map((skill) => (
            <span
              key={skill}
              className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
            >
              {skill}
            </span>
          ))}
        </div>
      ) : null}
      <span className="mt-2 text-sm font-medium text-indigo-600 group-hover:underline">
        View &amp; apply →
      </span>
    </Link>
  );
}