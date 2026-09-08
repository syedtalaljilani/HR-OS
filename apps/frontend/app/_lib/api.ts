export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Job = {
  id: string;
  title: string;
  description: string | null;
  requirements: Record<string, unknown> | null;
  location: string | null;
  salary_min: string | null;
  salary_max: string | null;
  status: string;
};

export type TrackingHistoryItem = {
  from_status: string | null;
  to_status: string;
  reason: string | null;
  created_at: string;
};

export type TrackingSnapshot = {
  application_id: string;
  status: string;
  candidate_name: string;
  job_title: string;
  created_at: string;
  updated_at: string;
  status_history: TrackingHistoryItem[];
};

export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/public/jobs`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load jobs (${res.status})`);
  return res.json();
}

export async function getJob(id: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/public/jobs/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) throw new Error("not-found");
  if (!res.ok) throw new Error(`Failed to load job (${res.status})`);
  return res.json();
}

export async function trackApplication(
  token: string
): Promise<TrackingSnapshot> {
  const res = await fetch(
    `${API_BASE}/public/applications/${encodeURIComponent(token)}`,
    { cache: "no-store" }
  );
  if (res.status === 404) throw new Error("not-found");
  if (!res.ok) throw new Error(`Failed to load application (${res.status})`);
  return res.json();
}

export function formatSalary(
  min: string | null,
  max: string | null
): string | null {
  const money = (v: string) =>
    Number(v).toLocaleString("en-PK", {
      style: "currency",
      currency: "PKR",
      maximumFractionDigits: 0,
    });
  if (min && max) return `${money(min)} – ${money(max)}`;
  if (min) return `From ${money(min)}`;
  if (max) return `Up to ${money(max)}`;
  return null;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatStatus(value: string): string {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}