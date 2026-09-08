import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "HR OS — Careers",
  description: "Find open positions and apply with HR OS.",
};

export default function SiteLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <header className="border-b border-zinc-200">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-lg font-bold text-zinc-900">
            HR <span className="text-indigo-600">OS</span>
          </Link>
          <nav className="flex items-center gap-6 text-sm font-medium text-zinc-600">
            <Link href="/" className="hover:text-zinc-900">
              Jobs
            </Link>
            <Link href="/track" className="hover:text-zinc-900">
              Track application
            </Link>
          </nav>
        </div>
      </header>
      {children}
      <footer className="border-t border-zinc-200">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-6 text-sm text-zinc-500">
          <span>© {new Date().getFullYear()} HR OS</span>
          <Link href="/login" className="hover:text-zinc-800">
            HR login
          </Link>
        </div>
      </footer>
    </>
  );
}