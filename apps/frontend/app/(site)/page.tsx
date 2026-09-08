import Link from "next/link";

import JobCard from "@/app/_components/JobCard";
import { listJobs } from "@/app/_lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let jobs;
  let error: string | null = null;
  try {
    jobs = await listJobs();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Unknown error";
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-6 py-12">
      <section className="mb-10 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900">
          Build your career with <span className="text-indigo-600">HR OS</span>
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-lg text-zinc-600">
          Explore open positions, apply with your CV in minutes, and track your
          application status in real time.
        </p>
        <Link
          href="/track"
          className="mt-5 inline-flex items-center rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
        >
          Already applied? Track your application
        </Link>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold text-zinc-900">
          Open positions
        </h2>
        {error ? (
          <p className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">
            Could not load jobs right now ({error}). Please try again later.
          </p>
        ) : jobs && jobs.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        ) : (
          <p className="rounded-lg bg-zinc-100 px-4 py-3 text-sm text-zinc-600">
            No open positions right now. Please check back soon.
          </p>
        )}
      </section>
    </main>
  );
}