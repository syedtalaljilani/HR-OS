export default function Kpi({
  label,
  value,
  icon,
  tone,
  hint,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  tone: string;
  hint?: string;
}) {
  return (
    <div className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-zinc-500">{label}</span>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center ${tone}`}>
          {icon}
        </span>
      </div>
      <p className="mt-2 text-3xl font-bold tracking-tight text-zinc-900">
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-zinc-400">{hint}</p> : null}
    </div>
  );
}