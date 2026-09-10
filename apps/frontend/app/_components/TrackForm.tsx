"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function TrackForm() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [error, setError] = useState("");

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = token.trim();
    if (!value) {
      setError("Please enter your tracking token.");
      return;
    }
    setError("");
    router.push(`/track/${encodeURIComponent(value)}`);
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full max-w-md flex-col gap-3">
      <label htmlFor="token" className="text-sm font-medium text-zinc-700">
        Tracking token
      </label>
      <input
        id="token"
        value={token}
        onChange={(event) => setToken(event.target.value)}
        placeholder="Paste your tracking token"
        className="w-full  border border-zinc-300 px-3 py-2 text-sm font-mono focus:border-navy-500 focus:outline-none focus:ring-1 focus:ring-navy-500"
      />
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      <button
        type="submit"
        className="inline-flex items-center justify-center  bg-navy-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-700"
      >
        Track application
      </button>
    </form>
  );
}