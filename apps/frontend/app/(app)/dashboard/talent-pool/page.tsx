"use client";

import { useCallback, useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import Button from "@/app/hr/_components/Button";
import { Field, inputClass } from "@/app/hr/_components/Field";
import Modal, { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { LoadingScreen } from "@/app/hr/_components/Button";
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

  const load = useCallback(async (selectedFilter?: string) => {
    const query = selectedFilter ?? filter;
    const path = query ? `/talent-pool?status=${encodeURIComponent(query)}` : "/talent-pool";
    try {
      const [pool, jobList] = await Promise.all([
        api<TalentPoolEntry[]>(path),
        api<Job[]>("/jobs"),
      ]);
      setEntries(pool);
      setJobs(jobList);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load talent pool");
    }
  }, [filter]);

  useEffect(() => {
    void (async () => {
      await load("");
    })();
  }, [load]);

  async function contact(entry: TalentPoolEntry) {
    setBusyId(entry.id);
    try {
      await api(`/talent-pool/${entry.id}/contact`, { method: "POST" });
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
      <div className="flex flex-1 flex-col gap-4 p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (!entries) return <LoadingScreen />;

  const openJobs = jobs.filter((job) => job.status === "OPEN");

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Talent Pool</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Candidates worth reconsidering for future opportunities.
        </p>
      </div>

      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900">
          Match pool against a job
        </h2>
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
              No matching candidates found.
            </p>
          ) : (
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {matches.map((match) => (
                <div
                  key={match.candidate_id}
                  className="flex items-center justify-between rounded-xl border border-indigo-200 bg-indigo-50/50 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-zinc-900">
                      {match.candidate_name}
                    </p>
                    <p className="text-xs text-zinc-500">
                      Pool candidate
                    </p>
                  </div>
                  <span className="rounded-full bg-indigo-600 px-2.5 py-0.5 text-xs font-bold text-white">
                    {Math.round(match.similarity * 100)}%
                  </span>
                </div>
              ))}
            </div>
          )
        ) : null}
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold text-zinc-900">
            Pool members
          </h2>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => {
                setFilter("");
                load("");
              }}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                filter === ""
                  ? "bg-indigo-600 text-white"
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
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  filter === status
                    ? "bg-indigo-600 text-white"
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
            title="Talent pool is empty"
            description="Add candidates from the candidate review screen to build your talent pool."
          />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className="flex flex-col rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-zinc-900">
                      {entry.candidate_name}
                    </h3>
                    <p className="text-sm text-zinc-500">{entry.candidate_email}</p>
                  </div>
                  <Badge status={entry.status} />
                </div>
                <p className="mt-3 text-xs text-zinc-400">
                  Added {formatDate(entry.created_at)}
                  {entry.consent ? " • consent on file" : " • no consent"}
                </p>
                <div className="mt-4 flex items-center gap-2 border-t border-zinc-100 pt-4">
                  {entry.status === "ACTIVE" ? (
                    <Button
                      variant="secondary"
                      loading={busyId === entry.id}
                      onClick={() => contact(entry)}
                      className="px-3 py-1.5"
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
                    className="px-3 py-1.5"
                  >
                    Update status
                  </Button>
                </div>
              </div>
            ))}
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
            <Button onClick={saveStatus} loading={busyId === statusTarget?.id} disabled={!newStatus}>
              Save
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}