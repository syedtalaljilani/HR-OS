"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import Button from "@/app/hr/_components/Button";
import { Field, inputClass } from "@/app/hr/_components/Field";
import Modal, { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { TableSkeleton } from "@/app/hr/_components/Skeleton";
import {
  api,
  formatDate,
  formatStatus,
  type Job,
  type TalentPoolEntry,
  type TalentPoolMatch,
} from "@/app/hr/_lib/api";

const POOL_STATUSES = [
  "ACTIVE",
  "CONTACTED",
  "INTERESTED",
  "NOT_INTERESTED",
  "MOVED_TO_PIPELINE",
  "EXPIRED",
  "REMOVED",
];

export default function TalentPoolPage() {
  const [entries, setEntries] = useState<TalentPoolEntry[] | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [statusTarget, setStatusTarget] = useState<TalentPoolEntry | null>(null);
  const [newStatus, setNewStatus] = useState("");
  const [matchJobId, setMatchJobId] = useState("");
  const [matches, setMatches] = useState<TalentPoolMatch[] | null>(null);
  const [matching, setMatching] = useState(false);

  const load = useCallback(
    async (selectedFilter?: string) => {
      const query = selectedFilter ?? filter;
      const path = query
        ? `/talent-pool?status=${encodeURIComponent(query)}`
        : "/talent-pool";
      try {
        const [pool, jobList] = await Promise.all([
          api<TalentPoolEntry[]>(path),
          api<Job[]>("/jobs"),
        ]);
        setEntries(pool);
        setJobs(jobList);
        setError(null);
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Failed to load talent pool"
        );
      }
    },
    [filter]
  );

  useEffect(() => {
    void (async () => {
      await load("");
    })();
  }, [load]);

  async function contact(entry: TalentPoolEntry) {
    setBusyId(entry.id);
    try {
      await api(`/talent-pool/${entry.id}/contact`, { method: "POST" });
      setMatches(null);
      load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  async function saveStatus() {
    if (!statusTarget || !newStatus) return;
    setBusyId(statusTarget.id);
    try {
      await api(`/talent-pool/${statusTarget.id}/status`, {
        method: "PATCH",
        body: { status: newStatus },
      });
      setStatusTarget(null);
      load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  async function runMatch() {
    if (!matchJobId) return;
    setMatching(true);
    setMatches(null);
    try {
      const result = await api<{ matches: TalentPoolMatch[] }>(
        "/talent-pool/match",
        { method: "POST", body: { job_id: matchJobId, limit: 10 } }
      );
      setMatches(result.matches);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Match failed");
    } finally {
      setMatching(false);
    }
  }

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (!entries) {
    return (
      <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
        <div>
          <div className="skeleton h-6 w-40" />
          <div className="skeleton mt-2 h-3.5 w-72" />
        </div>
        <TableSkeleton rows={5} columns={4} />
      </div>
    );
  }

  const openJobs = jobs.filter((job) => job.status === "OPEN");

  return (
    <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
          Talent Pool
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Previously reviewed candidates you may want to reconsider later.
        </p>
      </div>

      <section className="border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900">
          Match pool against a job
        </h2>
        <p className="mt-0.5 text-xs text-zinc-400">
          AI similarity scoring between pool candidates and an open position.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select
            value={matchJobId}
            onChange={(event) => setMatchJobId(event.target.value)}
            className={`${inputClass()} max-w-sm`}
          >
            <option value="">Select an open job…</option>
            {openJobs.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </select>
          <Button onClick={runMatch} loading={matching} disabled={!matchJobId}>
            Find matches
          </Button>
        </div>
        {matches ? (
          matches.length === 0 ? (
            <p className="mt-4 text-sm text-zinc-500">
              No matching candidates found for this job.
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto border border-zinc-200">
              <table className="min-w-full divide-y divide-zinc-200 text-sm">
                <thead className="bg-violet-50/60 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
                  <tr>
                    <th className="px-4 py-2.5">Candidate</th>
                    <th className="px-4 py-2.5">AI similarity</th>
                    <th className="px-4 py-2.5 text-right">Evidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {matches.map((match) => (
                    <tr key={match.candidate_id} className="hover:bg-violet-50/40">
                      <td className="px-4 py-3 font-medium text-zinc-900">
                        {match.candidate_name ?? "Pool candidate"}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-2">
                          <span className="h-1.5 w-16 bg-zinc-100">
                            <span
                              className="block h-1.5 bg-violet-600"
                              style={{
                                width: `${Math.min(100, Math.round(match.similarity * 100))}%`,
                              }}
                            />
                          </span>
                          <span className="text-xs font-semibold text-zinc-700">
                            {Math.round(match.similarity * 100)}%
                          </span>
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-zinc-400">
                        Matched by {match.candidate_name ? "profile" : "CV"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : null}
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold text-zinc-900">Pool members</h2>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => {
                setFilter("");
                load("");
              }}
              className={`px-3 py-1 text-xs font-medium transition ${
                filter === ""
                  ? "bg-violet-600 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              All
            </button>
            {POOL_STATUSES.map((status) => (
              <button
                key={status}
                onClick={() => {
                  setFilter(status);
                  load(status);
                }}
                className={`px-3 py-1 text-xs font-medium transition ${
                  filter === status
                    ? "bg-violet-600 text-white"
                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                }`}
              >
                {formatStatus(status)}
              </button>
            ))}
          </div>
        </div>

        {entries.length === 0 ? (
          <EmptyState
            title="Your talent pool is empty"
            description="Candidates you save for future opportunities will appear here."
          />
        ) : (
          <div className="overflow-x-auto border border-zinc-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-zinc-200 text-sm">
              <thead className="bg-violet-50/60 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-5 py-3">Candidate</th>
                  <th className="px-5 py-3">Contact</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Added</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-violet-50/40">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-zinc-900">
                        {entry.candidate_name ?? "Pool candidate"}
                      </p>
                      {entry.source_application_id ? (
                        <Link
                          href={`/dashboard/candidates/${entry.source_application_id}`}
                          className="text-xs text-violet-600 hover:underline"
                        >
                          View application →
                        </Link>
                      ) : null}
                    </td>
                    <td className="px-5 py-3.5 text-zinc-600">
                      <p>{entry.candidate_email ?? "No email"}</p>
                      <p className="text-xs text-zinc-400">
                        {entry.consent ? "consent on file" : "no consent"}
                      </p>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge status={entry.status} />
                    </td>
                    <td className="px-5 py-3.5 text-zinc-500">
                      {formatDate(entry.created_at)}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center justify-end gap-2">
                        {entry.status === "ACTIVE" ? (
                          <Button
                            variant="secondary"
                            loading={busyId === entry.id}
                            onClick={() => contact(entry)}
                            className="px-3 py-1.5 text-xs"
                          >
                            Mark contacted
                          </Button>
                        ) : null}
                        <Button
                          variant="secondary"
                          onClick={() => {
                            setStatusTarget(entry);
                            setNewStatus("");
                          }}
                          className="px-3 py-1.5 text-xs"
                        >
                          Update status
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Modal
        open={statusTarget !== null}
        onClose={() => setStatusTarget(null)}
        title={`Update status — ${statusTarget?.candidate_name ?? ""}`}
      >
        <div className="flex flex-col gap-4">
          <Field label="New status *">
            <select
              value={newStatus}
              onChange={(event) => setNewStatus(event.target.value)}
              className={inputClass()}
            >
              <option value="">Select a status…</option>
              {POOL_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {formatStatus(status)}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setStatusTarget(null)}>
              Cancel
            </Button>
            <Button
              onClick={saveStatus}
              loading={busyId === statusTarget?.id}
              disabled={!newStatus}
            >
              Save
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}