import type { EvidenceItem } from "@/app/hr/_lib/api";

const CONFIG: Record<
  EvidenceItem["status"],
  { icon: React.ReactNode; tone: string; label: string; hint: string }
> = {
  MATCH: {
    tone: "bg-emerald-50 text-emerald-700 ring-emerald-300",
    label: "Matched",
    hint: "Verified",
    icon: (
      <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z" clipRule="evenodd" />
      </svg>
    ),
  },
  PARTIAL: {
    tone: "bg-amber-50 text-amber-700 ring-amber-300",
    label: "Partial",
    hint: "Partially verified",
    icon: (
      <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="currentColor">
        <path fillRule="evenodd" d="M18 10c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8 8 3.58 8 8Zm-8-5a1 1 0 0 1 1 1v3.5h3.5a1 1 0 1 1 0 2H11V14a1 1 0 1 1-2 0v-2.5H5.5a1 1 0 1 1 0-2H9V6a1 1 0 0 1 1-1Z" clipRule="evenodd" />
      </svg>
    ),
  },
  MISSING: {
    tone: "bg-rose-50 text-rose-700 ring-rose-300",
    label: "Missing",
    hint: "No evidence found",
    icon: (
      <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM8.28 7.22a.75.75 0 0 0-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 1 0 1.06 1.06L10 11.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L11.06 10l1.72-1.72a.75.75 0 0 0-1.06-1.06L10 8.94 8.28 7.22Z" clipRule="evenodd" />
      </svg>
    ),
  },
  UNCLEAR: {
    tone: "bg-zinc-100 text-zinc-600 ring-zinc-300",
    label: "Unclear",
    hint: "Verify manually",
    icon: (
      <svg viewBox="0 0 20 20" className="h-3.5 w-3.5 text-zinc-500" fill="currentColor">
        <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-8-3.5a1.5 1.5 0 0 1 1.5 1.5v.59c0 .3-.08.59-.24.84l-1.06 1.7a.75.75 0 0 1-1.3-.75l1.18-1.9a.75.75 0 0 0 .17-.48v-.6A.75.75 0 0 1 10 6.5ZM10.75 14a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" clipRule="evenodd" />
      </svg>
    ),
  },
};

export default function RequirementItem({ item }: { item: EvidenceItem }) {
  const config = CONFIG[item.status];
  return (
    <div className="border border-zinc-200 bg-white px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center ring-1 ring-inset ${config.tone}`}
          >
            {config.icon}
          </span>
          <div>
            <p className="text-sm font-medium text-zinc-900">
              {item.requirement}
            </p>
            <p className="text-xs text-zinc-500">{config.hint}</p>
          </div>
        </div>
        <span
          className={`shrink-0 px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${config.tone}`}
        >
          {config.label}
        </span>
      </div>
      {item.evidence ? (
        <p className="mt-2 border-l-2 border-zinc-200 pl-3 text-sm text-zinc-600">
          “{item.evidence}”
        </p>
      ) : (
        <p className="mt-2 pl-0 text-sm text-zinc-400">
          {item.status === "MISSING"
            ? "No direct evidence found in the CV."
            : "Related information found, but HR verification is recommended."}
        </p>
      )}
    </div>
  );
}