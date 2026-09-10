import { formatStatus } from "@/app/hr/_lib/api";

const PALETTE: Record<string, string> = {
  DRAFT: "bg-zinc-100 text-zinc-700 ring-zinc-300",
  OPEN: "bg-navy-50 text-navy-700 ring-navy-300",
  CLOSED: "bg-rose-50 text-rose-700 ring-rose-300",

  APPLIED: "bg-zinc-100 text-zinc-700 ring-zinc-300",
  PROCESSING: "bg-blue-50 text-blue-700 ring-blue-300",
  HR_REVIEW: "bg-navy-50 text-navy-700 ring-navy-300",
  SHORTLISTED: "bg-navy-50 text-navy-700 ring-navy-300",
  INTERVIEW_SCHEDULED: "bg-amber-50 text-amber-700 ring-amber-300",
  TECHNICAL_INTERVIEW: "bg-amber-50 text-amber-700 ring-amber-300",
  TECHNICAL_REVIEW: "bg-amber-50 text-amber-700 ring-amber-300",
  BEHAVIORAL_INTERVIEW: "bg-amber-50 text-amber-700 ring-amber-300",
  FINAL_REVIEW: "bg-orange-50 text-orange-700 ring-orange-300",
  SELECTED: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  HOLD: "bg-yellow-50 text-yellow-700 ring-yellow-300",
  REJECTED: "bg-rose-50 text-rose-700 ring-rose-300",

  ACTIVE: "bg-navy-50 text-navy-700 ring-navy-300",
  CONTACTED: "bg-blue-50 text-blue-700 ring-blue-300",
  INTERESTED: "bg-navy-50 text-navy-700 ring-navy-300",
  NOT_INTERESTED: "bg-zinc-100 text-zinc-600 ring-zinc-300",
  MOVED_TO_PIPELINE: "bg-navy-50 text-navy-700 ring-navy-300",
  EXPIRED: "bg-yellow-50 text-yellow-700 ring-yellow-300",
  REMOVED: "bg-rose-50 text-rose-700 ring-rose-300",
};

export default function Badge({ status }: { status: string }) {
  const classes =
    PALETTE[status] ?? "bg-zinc-100 text-zinc-700 ring-zinc-300";
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${classes}`}
    >
      {formatStatus(status)}
    </span>
  );
}