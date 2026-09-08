import Link from "next/link";
import { notFound } from "next/navigation";

import ApplicationTimeline from "@/app/_components/ApplicationTimeline";
import { trackApplication } from "@/app/_lib/api";

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
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-6 py-10">
      <Link href="/track" className="text-sm text-zinc-500 hover:text-zinc-800">
        ← Track another application
      </Link>

      <div className="mt-5 border border-zinc-200 bg-white p-6 sm:p-8">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
          {snapshot.job_title}
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Application ID:{" "}
          <span className="font-mono font-medium text-zinc-700">
            {snapshot.application_id}
          </span>
        </p>

        <div className="mt-8">
          <ApplicationTimeline
            status={snapshot.status}
            updatedAt={snapshot.updated_at}
          />
        </div>
      </div>
    </main>
  );
}