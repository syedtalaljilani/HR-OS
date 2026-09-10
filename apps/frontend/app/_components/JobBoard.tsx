"use client";

import { useState } from "react";

import JobCard from "@/app/_components/JobCard";
import type { Job } from "@/app/_lib/api";

export default function JobBoard({ jobs }: { jobs: Job[] }) {
  const [query, setQuery] = useState("");

  const visible = jobs.filter((job) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (
      job.title.toLowerCase().includes(q) ||
      (job.description ?? "").toLowerCase().includes(q) ||
      (job.location ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex flex-col gap-5">
      <div className="relative max-w-md">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
          />
        </svg>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search roles by title, skill or location"
          aria-label="Search open roles"
          className="w-full border border-zinc-300 bg-white py-2 pl-9 pr-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-navy-500 focus:outline-none focus:ring-1 focus:ring-navy-500"
        />
      </div>

      {visible.length === 0 ? (
        <div className="border border-dashed border-zinc-300 bg-white px-6 py-14 text-center">
          <p className="text-sm font-medium text-zinc-700">
            No positions match your search
          </p>
          <p className="mt-1 text-sm text-zinc-500">
            Try a different search or check back soon.
          </p>
        </div>
      ) : (
        <div className="border border-zinc-200 bg-white shadow-sm">
          {visible.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}