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
  const skills = Array.isArray(reqs.skills) ? reqs.skills.map(String) : [];
  const experience =
    typeof reqs.experience === "string" && reqs.experience.trim()
      ? reqs.experience.trim()
      : null;
  const education =
    typeof reqs.education === "string" && reqs.education.trim()
      ? reqs.education.trim()
      : null;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6 py-10">
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-800">
        ← Back to all jobs
      </Link>

      <div className="mt-5 flex flex-col gap-6 border border-zinc-200 bg-white p-6 sm:p-8">
        <header>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900">
            {job.title}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-zinc-500">
            {job.location ? <span>{job.location}</span> : null}
            {salary ? (
              <span className="border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 font-medium text-emerald-700">
                {salary}
              </span>
            ) : null}
          </div>
        </header>

        <a
          href="#apply"
          className="inline-flex items-center justify-center bg-navy-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-700"
        >
          Apply now
        </a>

        {job.description ? (
          <section>
            <h2 className="text-lg font-semibold text-zinc-900">
              About the role
            </h2>
            <p className="mt-2 whitespace-pre-line text-[15px] leading-relaxed text-zinc-700">
              {job.description}
            </p>
          </section>
        ) : null}

        {skills.length > 0 || experience || education ? (
          <section>
            <h2 className="text-lg font-semibold text-zinc-900">
              Requirements
            </h2>
            <div className="mt-3 flex flex-col gap-4">
              {skills.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Core skills
                  </p>
                  <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
                    {skills.map((skill) => (
                      <li
                        key={skill}
                        className="flex items-center gap-2 text-sm text-zinc-700"
                      >
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center bg-emerald-50 text-emerald-600">
                          <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                            <path
                              fillRule="evenodd"
                              d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </span>
                        {skill}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {experience ? (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Experience
                  </p>
                  <p className="mt-1 text-sm text-zinc-700">{experience}</p>
                </div>
              ) : null}
              {education ? (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Education
                  </p>
                  <p className="mt-1 text-sm text-zinc-700">{education}</p>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        <section id="apply" className="border-t border-zinc-200 pt-6">
          <h2 className="text-lg font-semibold text-zinc-900">
            Apply for this position
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            Fill in your details and attach your CV. It takes about a minute.
          </p>
          <div className="mt-5">
            <ApplyForm jobId={job.id} jobTitle={job.title} />
          </div>
        </section>
      </div>
    </main>
  );
}