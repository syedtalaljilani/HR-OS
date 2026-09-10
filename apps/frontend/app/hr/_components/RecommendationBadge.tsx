import { formatStatus } from "@/app/hr/_lib/api";

const PALETTE: Record<string, string> = {
  MATCH: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  PARTIAL: "bg-amber-50 text-amber-700 ring-amber-300",
  MISSING: "bg-rose-50 text-rose-700 ring-rose-300",
  UNCLEAR: "bg-zinc-100 text-zinc-600 ring-zinc-300",
};

export default function RecommendationBadge({
  recommendation,
}: {
  recommendation: string | null | undefined;
}) {
  const status = recommendation ?? "UNCLEAR";
  const text = formatStatus(status);
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${PALETTE[status]}`}
    >
      {text}
    </span>
  );
}