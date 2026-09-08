const STAGES = [
  { key: "submitted", label: "Application submitted" },
  { key: "processing", label: "Processing" },
  { key: "review", label: "Under review" },
  { key: "shortlisted", label: "Shortlisted" },
  { key: "interview", label: "Interview" },
  { key: "decision", label: "Final decision" },
];

const STAGE_INDEX: Record<string, number> = {
  APPLIED: 0,
  APPLICATION_RECEIVED: 0,
  PROCESSING: 1,
  HR_REVIEW: 2,
  HOLD: 2,
  SHORTLISTED: 3,
  INTERVIEW_SCHEDULED: 4,
  TECHNICAL_INTERVIEW: 4,
  TECHNICAL_REVIEW: 4,
  BEHAVIORAL_INTERVIEW: 4,
  FINAL_REVIEW: 4,
  SELECTED: 5,
  REJECTED: 5,
};

const STAGE_MESSAGE: Record<string, string> = {
  submitted: "Your application has been received. Thank you for applying.",
  processing: "We're processing your CV and reviewing your application.",
  review: "Your application is currently being reviewed.",
  shortlisted: "Your application has moved to the next stage.",
  interview: "Your application is being considered for an interview.",
  decision: "A final decision has been made.",
};

export default function ApplicationTimeline({
  status,
  updatedAt,
}: {
  status: string;
  updatedAt: string;
}) {
  const current = STAGE_INDEX[status] ?? 0;

  return (
    <div>
      <ol className="flex flex-col">
        {STAGES.map((stage, index) => {
          const state = index < current ? "done" : index === current ? "current" : "upcoming";
          return (
            <li key={stage.key} className="flex gap-4">
              <div className="flex flex-col items-center">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center text-xs font-semibold ${
                    state === "done"
                      ? "bg-emerald-500 text-white"
                      : state === "current"
                        ? "bg-violet-600 text-white"
                        : "border border-zinc-300 bg-white text-zinc-400"
                  }`}
                >
                  {state === "done" ? (
                    <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : state === "current" ? (
                    <span className={`h-2 w-2 rounded-full bg-white ${index < STAGES.length ? "step-pulse" : ""}`} />
                  ) : (
                    <span className="h-2 w-2 rounded-full bg-current" />
                  )}
                </span>
                {index < STAGES.length - 1 ? (
                  <span
                    className={`w-px flex-1 ${
                      index < current ? "bg-emerald-200" : "bg-zinc-200"
                    }`}
                  />
                ) : null}
              </div>
              <div className={`pb-6 ${state === "current" ? "" : ""}`}>
                <p
                  className={`text-sm font-medium ${
                    state === "upcoming"
                      ? "text-zinc-400"
                      : "text-zinc-900"
                  }`}
                >
                  {stage.label}
                  {state === "current" ? " •" : ""}
                </p>
                {state === "current" ? (
                  <p className="mt-1 max-w-md text-sm text-zinc-500">
                    {STAGE_MESSAGE[stage.key]}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
      <p className="border-t border-zinc-100 pt-4 text-xs text-zinc-400">
        Last updated {new Date(updatedAt).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}
      </p>
    </div>
  );
}