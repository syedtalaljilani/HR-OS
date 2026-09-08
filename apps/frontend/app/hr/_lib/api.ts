export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const TOKEN_KEY = "hros_access_token";
export const USER_KEY = "hros_user";

export type StoredUser = {
  id: string;
  name: string;
  email: string;
  role: "ADMIN" | "HR" | "INTERVIEWER";
  is_active: boolean;
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): StoredUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as StoredUser) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user: StoredUser): void {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

export async function login(
  email: string,
  password: string
): Promise<{ access_token: string; user: StoredUser }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(res.status, data?.detail ?? "Login failed");
  }
  return data;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
};

export async function api<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const data = await res.json().catch(() => null);
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- utility module has no router access
      window.location.assign("/login");
    }
    throw new ApiError(401, "Session expired");
  }
  if (!res.ok) {
    throw new ApiError(res.status, data?.detail ?? `Request failed (${res.status})`);
  }
  return data as T;
}

export type Job = {
  id: string;
  title: string;
  description: string | null;
  requirements: Record<string, unknown> | null;
  location: string | null;
  salary_min: string | null;
  salary_max: string | null;
  status: "DRAFT" | "OPEN" | "CLOSED";
  created_at: string;
};

export type ApplicationSummary = {
  id: string;
  application_id: string;
  candidate_id: string;
  job_id: string;
  expected_salary: string | null;
  status: string;
  consent: boolean;
  created_at: string;
  updated_at: string;
};

export type CVDocument = {
  id: string;
  file_name: string;
  mime_type: string | null;
  extraction_status: string;
  created_at: string;
};

export type Screening = {
  id: string;
  application_id: string;
  recommendation: string | null;
  score: string | null;
  evidence: { items?: EvidenceItem[] } | null;
  missing_requirements: { items?: EvidenceItem[] } | null;
  uncertainty: { items?: EvidenceItem[] } | null;
  model: string | null;
  hr_decision: string;
  reviewed_by: string | null;
  created_at: string;
};

export type EvidenceItem = {
  requirement: string;
  status: "MATCH" | "PARTIAL" | "MISSING" | "UNCLEAR";
  evidence: string | null;
};

export type HistoryItem = {
  id: string;
  application_id: string;
  from_status: string | null;
  to_status: string;
  changed_by: string | null;
  reason: string | null;
  created_at: string;
};

export type ApplicationDetail = ApplicationSummary & {
  candidate_name: string | null;
  candidate_email: string | null;
  candidate_phone: string | null;
  job_title: string | null;
  cv_documents: CVDocument[];
  screening: Screening | null;
  status_history: HistoryItem[];
};

export type Candidate = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  address: string | null;
  profile_data: Record<string, unknown> | null;
  created_at: string;
};

export type TalentPoolEntry = {
  id: string;
  candidate_id: string;
  source_application_id: string | null;
  status: string;
  consent: boolean;
  added_by: string | null;
  created_at: string;
  updated_at: string;
  candidate_name: string | null;
  candidate_email: string | null;
};

export type TalentPoolMatch = {
  candidate_id: string;
  candidate_name: string | null;
  similarity: number;
};

export function formatMoney(value: string | null): string | null {
  if (!value) return null;
  return Number(value).toLocaleString("en-PK", {
    style: "currency",
    currency: "PKR",
    maximumFractionDigits: 0,
  });
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatStatus(value: string): string {
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export async function getApplicationDetails(): Promise<ApplicationDetail[]> {
  const summaries = await api<ApplicationSummary[]>("/applications");
  const details = await Promise.all(
    summaries.map((app) =>
      api<ApplicationDetail>(`/applications/${app.id}`).catch(() => null)
    )
  );
  return details.filter((d): d is ApplicationDetail => d !== null);
}