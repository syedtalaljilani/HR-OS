import { formatStatus } from "@/app/_lib/api";

const PALETTE: Record<string, string> = {
  APPLIED: "bg-slate-100 text-slate-700 ring-slate-300",
  PROCESSING: "bg-blue-50 text-blue-700 ring-blue-300",
  HR_REVIEW: "bg-violet-50 text-violet-700 ring-violet-300",
  SHORTLISTED: "bg-cyan-50 text-cyan-700 ring-cyan-300",
  INTERVIEW_SCHEDULED: "bg-amber-50 text-amber-700 ring-amber-300",
  TECHNICAL_INTERVIEW: "bg-amber-50 text-amber-700 ring-amber-300",
  TECHNICAL_REVIEW: "bg-amber-50 text-amber-700 ring-amber-300",
  BEHAVIORAL_INTERVIEW: "bg-amber-50 text-amber-700 ring-amber-300",
  FINAL_REVIEW: "bg-orange-50 text-orange-700 ring-orange-300",
  SELECTED: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  HOLD: "bg-yellow-50 text-yellow-700 ring-yellow-300",
  REJECTED: "bg-rose-50 text-rose-700 ring-rose-300",
};

export default function StatusBadge({ status }: { status: string }) {
  const classes = PALETTE[status] ?? "bg-slate-100 text-slate-700 ring-slate-300";
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${classes}`}
    >
      {formatStatus(status)}
    </span>
  );
}