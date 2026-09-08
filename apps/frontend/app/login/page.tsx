"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";

import Button from "@/app/hr/_components/Button";
import { Field, inputClass } from "@/app/hr/_components/Field";
import { login, setToken, setStoredUser } from "@/app/hr/_lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(email.trim(), password);
      setToken(result.access_token);
      setStoredUser(result.user);
      router.push("/dashboard");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not reach the server. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-violet-50 px-6 py-16">
      <div className="w-full max-w-sm">
        <div className="relative border border-zinc-200 border-t-4 border-t-violet-600 bg-white p-8 shadow-md">
          <div className="mb-6 text-center">
            <Link href="/" className="text-2xl font-bold text-zinc-900">
              HR <span className="text-violet-600">OS</span>
            </Link>
            <p className="mt-1 text-sm text-zinc-500">
              Sign in to the recruitment console
            </p>
          </div>
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <Field label="Email">
              <input
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className={inputClass()}
                placeholder="admin@hros.com"
                autoComplete="email"
              />
            </Field>
            <Field label="Password">
              <input
                type="password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={inputClass()}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </Field>
            {error ? (
              <p className=" bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </p>
            ) : null}
            <Button type="submit" loading={submitting} className="w-full">
              Sign in
            </Button>
          </form>
        </div>
        <p className="mt-4 text-center text-xs text-zinc-400">
          Demo: admin@hros.com / admin12345
        </p>
      </div>
    </main>
  );
}