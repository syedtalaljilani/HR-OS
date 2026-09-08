export default function ErrorState({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center border border-rose-200 bg-rose-50/50 px-6 py-12 text-center">
      <span className="flex h-10 w-10 items-center justify-center bg-rose-500 text-white">
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
          />
        </svg>
      </span>
      <h3 className="mt-4 text-base font-semibold text-zinc-900">{title}</h3>
      {description ? (
        <p className="mt-1 max-w-md text-sm text-zinc-600">{description}</p>
      ) : null}
      {children ? <div className="mt-4 flex gap-2">{children}</div> : null}
    </div>
  );
}