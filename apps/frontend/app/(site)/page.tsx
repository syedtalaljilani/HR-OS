import Link from "next/link";

import JobBoard from "@/app/_components/JobBoard";
import { listJobs } from "@/app/_lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let jobs;
  let loadError: string | null = null;
  try {
    jobs = await listJobs();
  } catch (caught) {
    loadError = caught instanceof Error ? caught.message : "Unknown error";
  }

  const open = (jobs ?? []).filter((job) => job.status === "OPEN");

  return (
    <main className="flex-1">
      <section className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex w-full max-w-3xl flex-col items-center px-6 py-20 text-center">
          <span className="border border-navy-200 bg-navy-50 px-3 py-1 text-xs font-medium text-navy-700">
            Now hiring
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight text-zinc-900 sm:text-5xl">
            Find your next opportunity.
          </h1>
          <p className="mt-4 max-w-xl text-lg text-zinc-600">
            Explore current open roles, apply with your CV in minutes and
            track your application from submission to decision.
          </p>
          <a
            href="#positions"
            className="mt-7 inline-flex items-center bg-navy-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-700"
          >
            Explore open positions
          </a>
        </div>
      </section>

      <section id="positions" className="mx-auto flex w-full max-w-3xl flex-col px-6 py-14">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-zinc-900">Open positions</h2>
          <p className="mt-1 text-sm text-zinc-500">
            {open.length === 0
              ? "There are no open roles right now."
              : `${open.length} open role${open.length === 1 ? "" : "s"} available.`}
          </p>
        </div>

        {loadError ? (
          <div className="border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            We couldn&apos;t load the job list right now ({loadError}). Please
            try again later.
          </div>
        ) : open.length > 0 ? (
          <JobBoard jobs={open} />
        ) : (
          <div className="border border-dashed border-zinc-300 bg-white px-6 py-14 text-center">
            <p className="text-sm font-medium text-zinc-700">
              No open positions right now
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              Please check back soon. Meanwhile you can review previously
              applied roles with your tracking link.
            </p>
          </div>
        )}

        <div className="mt-12 border border-zinc-200 bg-navy-50/50 px-6 py-5 text-center">
          <p className="text-sm text-zinc-600">
            Already applied?{" "}
            <Link href="/track" className="font-medium text-navy-700 hover:underline">
              Track your application
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}