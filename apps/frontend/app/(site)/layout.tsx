import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "HR OS — Careers",
  description: "Find open positions and apply with HR OS.",
};

export default function SiteLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <header className="border-b border-navy-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2 text-lg font-bold text-zinc-900">
            <span className="flex h-8 w-8 items-center justify-center bg-navy-600 text-white">
              <svg className="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84 50.633 50.633 0 0 0-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5" />
              </svg>
            </span>
            HR <span className="text-navy-600">OS</span>
          </Link>
          <nav className="flex items-center gap-6 text-sm font-medium text-zinc-600">
            <Link href="/" className="hover:text-navy-700">
              Jobs
            </Link>
            <Link href="/track" className="hover:text-navy-700">
              Track application
            </Link>
          </nav>
        </div>
      </header>
      {children}
      <footer className="bg-navy-950 text-navy-200">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-8 text-sm">
          <span>© {new Date().getFullYear()} HR OS — modern hiring made simple.</span>
          <Link href="/login" className="border border-navy-600 bg-navy-600 px-4 py-2 text-xs font-semibold text-white hover:bg-navy-700">
            HR login
          </Link>
        </div>
      </footer>
    </>
  );
}