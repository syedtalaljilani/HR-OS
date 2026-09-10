import Link from "next/link";

import ApplyForm from "@/app/_components/ApplyForm";
import { getInvitation } from "@/app/_lib/api";

export const dynamic = "force-dynamic";

export default async function InviteApplyPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let invite;
  let error: string | null = null;
  try {
    invite = await getInvitation(token);
  } catch (caught) {
    error =
      caught instanceof Error
        ? caught.message
        : "This invitation is not valid";
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6 py-10">
      {!invite ? (
        <div className="flex flex-col items-center justify-center border border-zinc-200 bg-white px-6 py-16 text-center">
          <h1 className="text-2xl font-bold text-zinc-900">
            Invitation unavailable
          </h1>
          <p className="mt-3 max-w-md text-sm text-zinc-600">{error}</p>
          <Link
            href="/"
            className="mt-6 inline-flex items-center justify-center bg-navy-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-700"
          >
            Browse open positions
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <header className="flex flex-col gap-2 border border-zinc-200 bg-white p-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-navy-600">
              {invite.company_name ? `${invite.company_name} · ` : ""}
              Exclusive invitation
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-zinc-900">
              {invite.job_title}
            </h1>
            {invite.job_location ? (
              <p className="text-sm text-zinc-500">{invite.job_location}</p>
            ) : null}
            <p className="mt-2 text-sm text-zinc-600">
              Welcome{invite.candidate_name ? `, ${invite.candidate_name}` : ""}!
              Upload your latest CV to apply — fields are pre-filled from your
              profile; you can update them below.
            </p>
          </header>
          <ApplyForm
            jobId={invite.job_id}
            jobTitle={invite.job_title}
            inviteToken={token}
            prefill={{
              fullName: invite.candidate_name ?? undefined,
              email: invite.candidate_email ?? undefined,
            }}
          />
        </div>
      )}
    </main>
  );
}