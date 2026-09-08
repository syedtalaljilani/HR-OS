import Link from "next/link";
import { notFound } from "next/navigation";

import StatusBadge from "@/app/_components/StatusBadge";
import { formatDate, formatStatus, trackApplication } from "@/app/_lib/api";

export const dynamic = "force-dynamic";

export default async function TrackResultPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let snapshot;
  try {
    snapshot = await trackApplication(token);
  } catch (caught) {
    if (caught instanceof Error && caught.message === "not-found") notFound();
    throw caught;
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-6 py-12">
      <Link href="/track" className="text-sm text-zinc-500 hover:text-zinc-800">
        ← Track another application
      </Link>

      <div className="mt-4  border border-zinc-200 bg-white p-6 sm:p-8">
        <h1 className="text-2xl font-bold text-zinc-900">
          {snapshot.application_id}
        </h1>
        <p className="mt-2 text-zinc-600">
          {snapshot.candidate_name} — {snapshot.job_title}
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <StatusBadge status={snapshot.status} />
          <span className="text-xs text-zinc-400">
            Updated {formatDate(snapshot.updated_at)}
          </span>
        </div>

        <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Status timeline
        </h2>
        <ol className="mt-4 flex flex-col gap-4">
          {snapshot.status_history.map((entry, index) => (
            <li key={`${entry.to_status}-${entry.created_at}`} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-violet-500" />
                {index < snapshot.status_history.length - 1 ? (
                  <span className="h-full w-px bg-zinc-200" />
                ) : null}
              </div>
              <div className="flex-1 pb-2">
                <p className="text-sm font-medium text-zinc-800">
                  {entry.from_status
                    ? `${formatStatus(entry.from_status)} → ${formatStatus(entry.to_status)}`
                    : formatStatus(entry.to_status)}
                </p>
                <p className="text-xs text-zinc-500">
                  {formatDate(entry.created_at)}
                  {entry.reason ? ` — ${entry.reason}` : ""}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </main>
  );
}