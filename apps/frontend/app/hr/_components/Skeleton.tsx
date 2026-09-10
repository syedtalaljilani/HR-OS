export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function KpiSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="border border-zinc-200 bg-white p-5 shadow-sm"
        >
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="mt-3 h-8 w-16" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
}: {
  rows?: number;
  columns?: number;
}) {
  return (
    <div className="border border-zinc-200 bg-white shadow-sm">
      <div className="border-b border-zinc-200 bg-navy-50/60 px-5 py-3">
        <Skeleton className="h-3 w-32" />
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="flex items-center gap-6 border-b border-zinc-100 px-5 py-4 last:border-b-0"
          style={{ display: "grid", gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-3.5 w-full" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div>
        <Skeleton className="h-3.5 w-32" />
        <Skeleton className="mt-3 h-8 w-64" />
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="flex flex-col gap-2 lg:col-span-2">
          <Skeleton className="h-4 w-1/2" />
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
        <div className="flex flex-col gap-2 lg:col-span-3">
          <Skeleton className="h-4 w-1/3" />
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}