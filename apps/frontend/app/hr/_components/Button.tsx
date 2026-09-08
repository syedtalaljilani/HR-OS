"use client";

const VARIANTS: Record<string, string> = {
  primary: "bg-violet-600 text-white hover:bg-violet-700",
  secondary:
    "bg-white text-violet-700 ring-1 ring-inset ring-violet-300 hover:bg-violet-50",
  ghost: "text-violet-600 hover:bg-violet-50 hover:text-violet-900",
  danger:
    "bg-white text-rose-700 ring-1 ring-inset ring-rose-300 hover:bg-rose-50",
};

export default function Button({
  children,
  variant = "primary",
  loading = false,
  className = "",
  disabled,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof VARIANTS;
  loading?: boolean;
}) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 border border-transparent px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
    >
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : null}
      {children}
    </button>
  );
}

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-violet-600 border-t-transparent ${className}`}
    />
  );
}

export function LoadingScreen() {
  return (
    <div className="flex flex-1 items-center justify-center py-24">
      <Spinner className="h-8 w-8" />
    </div>
  );
}