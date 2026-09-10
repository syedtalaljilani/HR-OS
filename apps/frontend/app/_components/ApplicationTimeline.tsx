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

const TERMINAL_LABEL: Record<string, string> = {
  SELECTED: "Selected",
  REJECTED: "Rejected",
};

const TERMINAL_MESSAGE: Record<string, string> = {
  SELECTED: "Congratulations! Your application was successful.",
  REJECTED: "Unfortunately, your application was not successful at this time.",
};

const STAGE_MESSAGE: Record<string, string> = {
  submitted: "Your application has been received. Thank you for applying.",
  processing: "We're processing your CV and reviewing your application.",
  review: "Your application is currently being reviewed.",
  shortlisted: "Your application has moved to the next stage.",
  interview: "Your application is being considered for an interview.",
  decision: "A final decision has been made.",
};

type TimelineHistoryItem = {
  from_status: string | null;
  to_status: string;
};

export default function ApplicationTimeline({
  status,
  updatedAt,
  history = [],
}: {
  status: string;
  updatedAt: string;
  history?: TimelineHistoryItem[];
}) {
  const current = STAGE_INDEX[status] ?? 0;

  // Stages count as "done" only when the application actually occupied that
  // stage AND the progress was not later reverted. Walking the history forward:
  // moving ahead marks the destination stage; moving backward resets/cancels
  // any progress beyond the destination. This way a rejected or reverted
  // application never shows stages (shortlist, interview) it did not pass.
  const reached = new Set<number>();
  let maxStage = -1;
  for (const item of history) {
    const j =
      item.to_status !== undefined && STAGE_INDEX[item.to_status] !== undefined
        ? STAGE_INDEX[item.to_status]
        : undefined;
    if (j === undefined) continue;
    if (j > maxStage) {
      maxStage = j;
      reached.add(j);
    } else if (j < maxStage) {
      for (const s of Array.from(reached)) {
        if (s > j) reached.delete(s);
      }
      reached.add(j);
      maxStage = j;
    }
  }
  reached.add(current);

  const stateFor = (index: number) => {
    if (index === current) return "current";
    if (reached.has(index)) return "done";
    return "upcoming";
  };

  return (
    <div>
      <ol className="flex flex-col">
        {STAGES.map((stage, index) => {
          const state = stateFor(index);
          const label =
            index === current
              ? (TERMINAL_LABEL[status] ?? stage.label)
              : stage.label;
          return (
            <li key={stage.key} className="flex gap-4">
              <div className="flex flex-col items-center">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center text-xs font-semibold ${
                    state === "done"
                      ? "bg-emerald-500 text-white"
                      : state === "current"
                        ? "bg-navy-600 text-white"
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
                      stateFor(index + 1) === "done" || (index + 1 === current)
                        ? "bg-emerald-200"
                        : "bg-zinc-200"
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
                  {label}
                  {state === "current" ? " •" : ""}
                </p>
                {state === "current" ? (
                  <p className="mt-1 max-w-md text-sm text-zinc-500">
                    {TERMINAL_MESSAGE[status] ?? STAGE_MESSAGE[stage.key]}
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