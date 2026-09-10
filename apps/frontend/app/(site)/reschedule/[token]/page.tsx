import Link from "next/link";

import RescheduleForm from "@/app/_components/RescheduleForm";
import { getReschedule } from "@/app/_lib/api";

export const dynamic = "force-dynamic";

export default async function ReschedulePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let view;
  try {
    view = await getReschedule(token);
  } catch {
    return (
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-6 py-10">
        <div className="rounded-lg border border-zinc-200 bg-white p-6 text-center">
          <h1 className="text-lg font-semibold text-zinc-900">
            Link not recognised
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            This reschedule link is not valid or has expired. Reply to the
            interview email and we will help you from there.
          </p>
          <Link
            href="/"
            className="mt-4 inline-block text-sm text-navy-700 hover:underline"
          >
            ← Back to careers
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-6 py-10">
      <div className="rounded-t-xl bg-navy-700 px-6 py-5">
        <h1 className="text-xl font-bold text-white">
          {view.job_title}
        </h1>
        <p className="mt-0.5 text-sm text-navy-200">
          {view.candidate_name} · Manage your interview
        </p>
      </div>
      <div className="rounded-b-xl border border-t-0 border-zinc-200 bg-white p-6 sm:p-8">
        <RescheduleForm token={token} initial={view} />
      </div>
    </main>
  );
}