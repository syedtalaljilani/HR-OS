"use client";

import { useState } from "react";

import {
  submitReschedule,
  type RescheduleView,
} from "@/app/_lib/api";

function whenLabel(iso: string): string {
  return new Date(iso).toLocaleString("en-PK", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function RescheduleForm({
  token,
  initial,
}: {
  token: string;
  initial: RescheduleView;
}) {
  const [view, setView] = useState<RescheduleView>(initial);
  const [selected, setSelected] = useState<string | null>(null);
  const [remoteWanted, setRemoteWanted] = useState(false);
  const [remoteReason, setRemoteReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const currentIso = view.scheduled_at;
  const alternatives = (view.available_slots ?? []).filter(
    (iso) => iso !== currentIso
  );

  async function handleSubmit() {
    if (busy) return;
    const payload: { selected_slot?: string; remote_reason?: string } = {};
    if (selected) payload.selected_slot = selected;
    if (remoteWanted) payload.remote_reason = remoteReason.trim();
    if (!payload.selected_slot && !payload.remote_reason) {
      setError("Pick a new slot or request a remote interview first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await submitReschedule(token, payload);
      setView(updated);
      setSelected(null);
      setRemoteWanted(false);
      setRemoteReason("");
      setSuccess(
        payload.selected_slot
          ? "Thank you — your interview was rescheduled. A confirmation email is on its way."
          : "Your remote interview request has been sent to HR. They will reply here by email."
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not submit");
    } finally {
      setBusy(false);
    }
  }

  if (view.already_rescheduled) {
    return (
      <div className="border border-emerald-200 bg-emerald-50 p-6 text-sm text-emerald-800">
        This interview has already been handled. Check your email for your
        updated interview time.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm">
        <p className="font-medium text-zinc-900">
          Current interview:{" "}
          <span className="font-semibold">{whenLabel(currentIso)}</span>
        </p>
        {view.location ? (
          <p className="mt-1 text-zinc-600">{view.location}</p>
        ) : null}
        {view.notes ? (
          <p className="mt-0.5 text-xs text-zinc-500">{view.notes}</p>
        ) : null}
        {!remoteWanted ? (
          <p className="mt-2 text-xs text-zinc-500">
            Not available at this time? Pick one of the slots below.
          </p>
        ) : null}
      </div>

      {!remoteWanted ? (
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
            Choose an available slot
          </h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {alternatives.length === 0 ? (
              <p className="text-sm text-zinc-500">
                No alternative slots listed right now — reply to the email to
                arrange another time.
              </p>
            ) : (
              alternatives.map((iso) => {
                const active = selected === iso;
                return (
                  <button
                    key={iso}
                    type="button"
                    onClick={() => setSelected(active ? null : iso)}
                    className={`rounded-lg border px-4 py-3 text-left text-sm transition ${
                      active
                        ? "border-navy-600 bg-navy-50 text-navy-700"
                        : "border-zinc-200 bg-white text-zinc-700 hover:border-navy-300"
                    }`}
                  >
                    <svg
                      className={`mr-2 inline h-4 w-4 ${
                        active ? "text-navy-600" : "text-zinc-300"
                      }`}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <circle cx="12" cy="12" r="9" />
                      {active ? <circle cx="12" cy="12" r="4" fill="currentColor" /> : null}
                    </svg>
                    {whenLabel(iso)}
                  </button>
                );
              })
            )}
          </div>
        </div>
      ) : null}

      <div className="rounded-lg border border-navy-200 bg-navy-50/50 p-4">
        <label className="flex items-start gap-3 text-sm">
          <input
            type="checkbox"
            checked={remoteWanted}
            onChange={(event) => setRemoteWanted(event.target.checked)}
            className="mt-0.5 h-4 w-4 accent-navy-600"
          />
          <span>
            <span className="font-medium text-zinc-900">
              Request a remote interview
            </span>
            <span className="block text-xs text-zinc-500">
              I can&apos;t visit in person — please arrange a remote interview.
              HR will review your request.
            </span>
          </span>
        </label>
        {remoteWanted ? (
          <textarea
            value={remoteReason}
            onChange={(event) => setRemoteReason(event.target.value)}
            rows={3}
            placeholder="Explain why you need a remote interview…"
            className="mt-3 w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-navy-500 focus:outline-none"
          />
        ) : null}
      </div>

      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {success}
        </p>
      ) : null}

      <button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={
          busy ||
          (!selected && !(remoteWanted && remoteReason.trim()))
        }
        className="rounded-lg bg-navy-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busy ? "Submitting…" : "Send my request"}
      </button>
    </div>
  );
}