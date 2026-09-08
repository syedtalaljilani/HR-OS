"use client";

import Link from "next/link";
import { useState } from "react";

import { API_BASE } from "@/app/_lib/api";

type ApplyState = {
  status: "idle" | "submitting";
  error?: string;
  success?: {
    applicationId: string;
    trackingToken: string;
  };
};

export default function ApplyForm({
  jobId,
  jobTitle,
}: {
  jobId: string;
  jobTitle: string;
}) {
  const [state, setState] = useState<ApplyState>({ status: "idle" });

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState({ status: "submitting" });

    const form = event.currentTarget;
    const body = new FormData(form);
    body.set("consent", (form.elements.namedItem("consent") as HTMLInputElement)
      .checked
      ? "true"
      : "false");

    try {
      const res = await fetch(`${API_BASE}/public/jobs/${jobId}/apply`, {
        method: "POST",
        body,
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail =
          typeof data?.detail === "string"
            ? data.detail
            : Array.isArray(data?.detail) && typeof data.detail[0]?.msg === "string"
              ? data.detail[0].msg
              : `Request failed (${res.status})`;
        setState({ status: "idle", error: detail });
        return;
      }
      const token = String(data.trackingUrl ?? "")
        .split("/")
        .pop();
      setState({
        status: "idle",
        success: {
          applicationId: data.applicationId,
          trackingToken: token || "",
        },
      });
    } catch {
      setState({
        status: "idle",
        error: "Could not reach the server. Please try again.",
      });
    }
  }

  if (state.success) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
        <h3 className="text-lg font-semibold text-emerald-900">
          Application submitted successfully
        </h3>
        <p className="mt-1 text-sm text-emerald-800">
          Application ID:{" "}
          <span className="font-mono font-semibold">
            {state.success.applicationId}
          </span>
        </p>
        <p className="mt-2 text-sm text-emerald-800">
          Use your tracking link to follow the progress of your application.
        </p>
        <Link
          href={`/track/${state.success.trackingToken}`}
          className="mt-4 inline-flex items-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          Track my application
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div>
        <label htmlFor="full_name" className="mb-1 block text-sm font-medium text-zinc-700">
          Full name *
        </label>
        <input
          id="full_name"
          name="full_name"
          required
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>
      <div>
        <label htmlFor="email" className="mb-1 block text-sm font-medium text-zinc-700">
          Email *
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="phone" className="mb-1 block text-sm font-medium text-zinc-700">
            Phone
          </label>
          <input
            id="phone"
            name="phone"
            className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="expected_salary" className="mb-1 block text-sm font-medium text-zinc-700">
            Expected salary
          </label>
          <input
            id="expected_salary"
            name="expected_salary"
            type="number"
            min="0"
            step="0.01"
            className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>
      <div>
        <label htmlFor="address" className="mb-1 block text-sm font-medium text-zinc-700">
          Address
        </label>
        <input
          id="address"
          name="address"
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>
      <div>
        <label htmlFor="file" className="mb-1 block text-sm font-medium text-zinc-700">
          Resume / CV * (PDF, DOCX or TXT, max 5 MB)
        </label>
        <input
          id="file"
          name="file"
          type="file"
          required
          accept=".pdf,.docx,.doc,.txt"
          className="block w-full text-sm text-zinc-600 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
        />
      </div>
      <label className="flex items-start gap-2 text-sm text-zinc-600">
        <input
          type="checkbox"
          name="consent"
          required
          className="mt-0.5 h-4 w-4 rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
        />
        <span>
          I consent to {jobTitle && <>my application for {jobTitle} and</>} my
          personal data being processed for recruitment purposes by HR OS. *
        </span>
      </label>
      {state.error ? (
        <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {state.error}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={state.status === "submitting"}
        className="mt-2 inline-flex w-full items-center justify-center rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
      >
        {state.status === "submitting" ? "Submitting…" : "Submit application"}
      </button>
    </form>
  );
}