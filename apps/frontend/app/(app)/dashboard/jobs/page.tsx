"use client";

import { useCallback, useEffect, useState } from "react";

import Badge from "@/app/hr/_components/Badge";
import Button from "@/app/hr/_components/Button";
import { Field, inputClass } from "@/app/hr/_components/Field";
import Modal, { EmptyState, ErrorNote } from "@/app/hr/_components/Modal";
import { LoadingScreen } from "@/app/hr/_components/Button";
import { api, formatDate, formatMoney, type Job } from "@/app/hr/_lib/api";

type JobForm = {
  title: string;
  location: string;
  salary_min: string;
  salary_max: string;
  description: string;
};

const EMPTY_FORM: JobForm = {
  title: "",
  location: "",
  salary_min: "",
  salary_max: "",
  description: "",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Job | null>(null);
  const [form, setForm] = useState<JobForm>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [aiInput, setAiInput] = useState("");
  const [aiTitle, setAiTitle] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setJobs(await api<Job[]>("/jobs"));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load jobs");
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function generateWithAI() {
    setAiBusy(true);
    setAiError(null);
    try {
      const draft = await api<{
        description: string;
        model: string | null;
      }>("/jobs/assistant/generate", {
        method: "POST",
        body: {
          user_input: aiInput,
          job_title: aiTitle || form.title || null,
        },
      });
      setForm({
        ...form,
        title: form.title || aiTitle,
        description: draft.description || form.description,
      });
    } catch (caught) {
      setAiError(
        caught instanceof Error ? caught.message : "Generation failed"
      );
    } finally {
      setAiBusy(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setAiInput("");
    setAiTitle("");
    setAiError(null);
    setModalOpen(true);
  }

  function openEdit(job: Job) {
    setEditing(job);
    setForm({
      title: job.title,
      location: job.location ?? "",
      salary_min: job.salary_min ?? "",
      salary_max: job.salary_max ?? "",
      description: job.description ?? "",
    });
    setFormError(null);
    setAiInput("");
    setAiTitle("");
    setAiError(null);
    setModalOpen(true);
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      const body = {
        title: form.title,
        location: form.location || null,
        salary_min: form.salary_min ? Number(form.salary_min) : null,
        salary_max: form.salary_max ? Number(form.salary_max) : null,
        description: form.description || null,
      };
      if (editing) {
        await api(`/jobs/${editing.id}`, { method: "PATCH", body });
      } else {
        await api("/jobs", { method: "POST", body });
      }
      setModalOpen(false);
      load();
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : "Failed to save job");
    } finally {
      setSaving(false);
    }
  }

  async function togglePublish(job: Job) {
    setBusyId(job.id);
    try {
      if (job.status === "OPEN") {
        await api(`/jobs/${job.id}/close`, { method: "POST" });
      } else if (job.status === "DRAFT") {
        await api(`/jobs/${job.id}/publish`, { method: "POST" });
      }
      load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (!jobs) return <LoadingScreen />;

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Jobs</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Create and manage job openings.
          </p>
        </div>
        <Button onClick={openCreate}>New job</Button>
      </div>

      {jobs.length === 0 ? (
        <EmptyState
          title="No jobs yet"
          description="Create your first job posting to start receiving applications."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {jobs.map((job) => {
            const salary = formatMoney(job.salary_min) ?? formatMoney(job.salary_max);
            return (
              <div
                key={job.id}
                className="flex flex-col  border border-zinc-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-base font-semibold text-zinc-900">
                    {job.title}
                  </h2>
                  <Badge status={job.status} />
                </div>
                <p className="mt-1 text-sm text-zinc-500">
                  {job.location || "Remote"}{" "}
                  {salary ? `• ${salary}` : ""}
                </p>
                {job.description ? (
                  <p className="mt-2 line-clamp-2 text-sm text-zinc-600">
                    {job.description}
                  </p>
                ) : null}
                <div className="mt-4 flex items-center gap-2 border-t border-zinc-100 pt-4">
                  <Button
                    variant="secondary"
                    onClick={() => openEdit(job)}
                    className="px-3 py-1.5"
                  >
                    Edit
                  </Button>
                  {job.status === "OPEN" ? (
                    <Button
                      variant="danger"
                      loading={busyId === job.id}
                      onClick={() => togglePublish(job)}
                      className="px-3 py-1.5"
                    >
                      Close
                    </Button>
                  ) : job.status === "DRAFT" ? (
                    <Button
                      loading={busyId === job.id}
                      onClick={() => togglePublish(job)}
                      className="px-3 py-1.5"
                    >
                      Publish
                    </Button>
                  ) : null}
                  <span className="ml-auto text-xs text-zinc-400">
                    Created {formatDate(job.created_at)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Edit job" : "New job"}
      >
        <form onSubmit={save} className="flex flex-col gap-4">
          <Field label="Title *">
            <input
              required
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              className={inputClass()}
            />
          </Field>

          <div className="border border-navy-200 bg-navy-50/50 p-4">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center bg-navy-600 text-white">
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
                </svg>
              </span>
              <span className="text-sm font-semibold text-navy-700">
                Writing assistant
              </span>
            </div>
            <p className="mt-2 text-xs text-zinc-500">
              Describe the role in your own words, or give a short prompt, and a
              first-draft job description is written for you. Review it in the
              form below before saving.
            </p>
            <div className="mt-3 flex flex-col gap-2">
              <input
                value={aiTitle}
                onChange={(event) => setAiTitle(event.target.value)}
                className={inputClass("bg-white")}
                placeholder="Job title (optional)"
              />
              <textarea
                rows={3}
                value={aiInput}
                onChange={(event) => setAiInput(event.target.value)}
                className={inputClass("bg-white")}
                placeholder="e.g. We need a senior backend developer with 3+ years of FastAPI experience, strong PostgreSQL skills, and experience building scalable APIs..."
              />
              {aiError ? <ErrorNote message={aiError} /> : null}
              <Button
                type="button"
                variant="secondary"
                loading={aiBusy}
                disabled={!aiInput.trim()}
                onClick={generateWithAI}
              >
                Generate job description
              </Button>
            </div>
          </div>

          <Field label="Location">
            <input
              value={form.location}
              onChange={(event) =>
                setForm({ ...form, location: event.target.value })
              }
              className={inputClass()}
              placeholder="e.g. Lahore, Pakistan"
            />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Salary min (PKR)">
              <input
                type="number"
                min="0"
                value={form.salary_min}
                onChange={(event) =>
                  setForm({ ...form, salary_min: event.target.value })
                }
                className={inputClass()}
              />
            </Field>
            <Field label="Salary max (PKR)">
              <input
                type="number"
                min="0"
                value={form.salary_max}
                onChange={(event) =>
                  setForm({ ...form, salary_max: event.target.value })
                }
                className={inputClass()}
              />
            </Field>
          </div>
          <Field label="Description">
            <textarea
              rows={4}
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
              className={inputClass()}
            />
          </Field>
          {formError ? <ErrorNote message={formError} /> : null}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={saving}>
              {editing ? "Save changes" : "Create job"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}