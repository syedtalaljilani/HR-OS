"use client";

import Link from "next/link";
import { useState } from "react";

import FileUpload from "@/app/_components/FileUpload";
import { API_BASE } from "@/app/_lib/api";

type ApplyState = {
  status: "idle" | "submitting" | "processing";
  error?: string;
  success?: {
    applicationId: string;
    trackingToken: string;
  };
};

const inputClass =
  "w-full border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500";

function FieldLabel({ htmlFor, children }: { htmlFor: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-zinc-700">
      {children}
    </label>
  );
}

const PROCESS_STEPS = [
  { done: true, label: "Application submitted" },
  { done: true, label: "CV uploaded" },
  { done: false, active: true, label: "Processing CV" },
  { done: false, active: false, label: "AI screening" },
];

function ProcessingPanel({ jobTitle }: { jobTitle: string }) {
  return (
    <div className="flex flex-col items-center py-10">
      <div className="flex gap-3">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="step-pulse h-2.5 w-2.5 rounded-full bg-violet-600"
            style={delay ? { animationDelay: `${delay}ms` } : undefined}
          />
        ))}
      </div>
      <h3 className="mt-5 text-lg font-semibold text-zinc-900">
        We&apos;re processing your application
      </h3>
      <p className="mt-1 text-sm text-zinc-500">
        {jobTitle} — this usually takes a few seconds.
      </p>
      <ul className="mt-6 flex w-full max-w-xs flex-col gap-2">
        {PROCESS_STEPS.map((step) => (
          <li key={step.label} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center ${
                step.done
                  ? "bg-emerald-500 text-white"
                  : step.active
                    ? "step-pulse bg-violet-600 text-white"
                    : "border border-zinc-300 text-zinc-400"
              }`}
            >
              {step.done ? (
                <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z" clipRule="evenodd" />
                </svg>
              ) : step.active ? (
                <span className="h-1.5 w-1.5 rounded-full bg-white" />
              ) : (
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
              )}
            </span>
            <span className={step.done || step.active ? "text-zinc-900" : "text-zinc-400"}>
              {step.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

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
    setState({ status: "processing", error: undefined });

    const form = event.currentTarget;
    const body = new FormData(form);
    body.set(
      "consent",
      (form.elements.namedItem("consent") as HTMLInputElement).checked
        ? "true"
        : "false"
    );

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
      const token = String(data.trackingUrl ?? "").split("/").pop();
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
        error: "We couldn't submit your application. Please check your connection and try again.",
      });
    }
  }

  if (state.status === "processing") {
    return <ProcessingPanel jobTitle={jobTitle} />;
  }

  if (state.success) {
    return (
      <div className="flex flex-col items-center border border-emerald-200 bg-emerald-50/50 px-6 py-10 text-center">
        <span className="flex h-12 w-12 items-center justify-center bg-emerald-500 text-white">
          <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
        </span>
        <h3 className="mt-4 text-xl font-bold text-zinc-900">
          Application submitted successfully
        </h3>
        <p className="mt-1 text-sm text-zinc-600">
          Thank you for applying for {jobTitle}. Your application is now being
          processed.
        </p>
        <p className="mt-4 text-sm text-zinc-500">
          Application ID{" "}
          <span className="font-mono font-semibold text-zinc-900">
            {state.success.applicationId}
          </span>
        </p>
        <Link
          href={`/track/${state.success.trackingToken}`}
          className="mt-5 inline-flex items-center bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700"
        >
          Track my application
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-4">
        <legend className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Personal information
        </legend>
        <div>
          <FieldLabel htmlFor="full_name">Full name *</FieldLabel>
          <input id="full_name" name="full_name" required className={inputClass} />
        </div>
        <div>
          <FieldLabel htmlFor="email">Email *</FieldLabel>
          <input id="email" name="email" type="email" required className={inputClass} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <FieldLabel htmlFor="phone">Phone</FieldLabel>
            <input id="phone" name="phone" className={inputClass} />
          </div>
          <div>
            <FieldLabel htmlFor="expected_salary">Expected salary (PKR)</FieldLabel>
            <input
              id="expected_salary"
              name="expected_salary"
              type="number"
              min="0"
              step="0.01"
              className={inputClass}
            />
          </div>
        </div>
        <div>
          <FieldLabel htmlFor="address">Address</FieldLabel>
          <input id="address" name="address" className={inputClass} />
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          CV
        </legend>
        <FileUpload
          name="file"
          maxSizeMb={10}
          onClearError={() => setState({ ...state, error: undefined })}
        />
      </fieldset>

      <label className="flex items-start gap-2 text-sm text-zinc-600">
        <input
          type="checkbox"
          name="consent"
          required
          className="mt-0.5 h-4 w-4 border-zinc-300 text-violet-600 focus:ring-violet-500"
        />
        <span>
          I consent to my application for {jobTitle} and my personal data being
          processed for recruitment purposes by HR OS. *
        </span>
      </label>

      {state.error ? (
        <p className="border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {state.error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={state.status === "submitting"}
        className="inline-flex w-full items-center justify-center bg-violet-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-violet-700 disabled:opacity-60"
      >
        {state.status === "submitting" ? "Submitting…" : "Submit application"}
      </button>
    </form>
  );
}