import Link from "next/link";
import { notFound } from "next/navigation";

import ApplyForm from "@/app/_components/ApplyForm";
import { formatSalary, getJob } from "@/app/_lib/api";

export const dynamic = "force-dynamic";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let job;
  try {
    job = await getJob(id);
  } catch (caught) {
    if (caught instanceof Error && caught.message === "not-found") notFound();
    throw caught;
  }

  const salary = formatSalary(job.salary_min, job.salary_max);
  const reqs = (job.requirements ?? {}) as Record<string, unknown>;

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-6 py-12">
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-800">
        ← Back to all jobs
      </Link>
      <div className="mt-4 rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8">
        <h1 className="text-3xl font-bold text-zinc-900">{job.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-zinc-500">
          {salary ? (
            <span className="rounded-full bg-emerald-50 px-3 py-1 font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
              {salary}
            </span>
          ) : null}
          {job.location ? <span>{job.location}</span> : null}
        </div>
        {job.description ? (
          <p className="mt-6 whitespace-pre-line text-zinc-700">
            {job.description}
          </p>
        ) : null}
        {Object.entries(reqs).length > 0 ? (
          <div className="mt-6 flex flex-col gap-4">
            {Object.entries(reqs).map(([section, value]) => {
              if (typeof value === "string" && value.trim()) {
                return (
                  <div key={section}>
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
                      {section.replaceAll("_", " ")}
                    </h3>
                    <p className="mt-1 text-sm text-zinc-700">{value}</p>
                  </div>
                );
              }
              if (Array.isArray(value) && value.length > 0) {
                return (
                  <div key={section}>
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
                      {section.replaceAll("_", " ")}
                    </h3>
                    <ul className="mt-1 flex flex-wrap gap-1.5">
                      {value.map((item) => (
                        <li
                          key={String(item)}
                          className="rounded-md bg-zinc-100 px-2 py-0.5 text-sm text-zinc-700"
                        >
                          {String(item)}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              }
              return null;
            })}
          </div>
        ) : null}
        <div id="apply" className="mt-8 border-t border-zinc-200 pt-8">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900">
            Apply for this position
          </h2>
          <ApplyForm jobId={job.id} jobTitle={job.title} />
        </div>
      </div>
    </main>
  );
}