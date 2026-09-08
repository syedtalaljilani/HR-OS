import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HR OS — Careers",
  description: "Find open positions and apply with HR OS.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-white">
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
            <span>AI-assisted recruitment</span>
          </div>
        </footer>
      </body>
    </html>
  );
}