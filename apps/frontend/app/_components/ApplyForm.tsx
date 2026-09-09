"use client";

import Link from "next/link";
import { useState } from "react";

import FileUpload from "@/app/_components/FileUpload";
import { API_BASE } from "@/app/_lib/api";

type ApplyState = {
  status: "idle" | "extracting" | "submitting" | "processing";
  error?: string;
  success?: {
    applicationId: string;
    trackingToken: string;
  };
};

type ExtractedProfile = {
  name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  expected_salary: string | null;
  summary: string | null;
  skills?: unknown[];
  languages?: unknown[];
  interests?: unknown[];
  links?: unknown[];
  education?: unknown[];
  experience?: unknown[];
  projects?: unknown[];
  certifications?: unknown[];
  publications?: unknown[];
};

type ObjectSectionDef = {
  key: string;
  label: string;
  fields: { key: string; label: string; placeholder: string; full?: boolean }[];
  empty: Record<string, string>;
};

const OBJECT_SECTIONS: ObjectSectionDef[] = [
  {
    key: "education",
    label: "Education",
    fields: [
      { key: "degree", label: "Degree", placeholder: "e.g. BSCS" },
      { key: "institution", label: "Institution", placeholder: "University / college" },
      { key: "years", label: "Years", placeholder: "e.g. 2020 – 2024" },
    ],
    empty: { degree: "", institution: "", years: "" },
  },
  {
    key: "experience",
    label: "Work experience",
    fields: [
      { key: "position", label: "Position", placeholder: "e.g. Senior AI Engineer" },
      { key: "company", label: "Company", placeholder: "Company name" },
      { key: "years", label: "Years", placeholder: "e.g. Jan 2025 – Oct 2025" },
      {
        key: "description",
        label: "Description",
        placeholder: "What you did…",
        full: true,
      },
    ],
    empty: { position: "", company: "", years: "", description: "" },
  },
  {
    key: "projects",
    label: "Projects",
    fields: [
      { key: "name", label: "Project", placeholder: "Project name" },
      { key: "link", label: "Link", placeholder: "URL (optional)" },
      {
        key: "description",
        label: "Description",
        placeholder: "What it is…",
        full: true,
      },
    ],
    empty: { name: "", link: "", description: "" },
  },
  {
    key: "certifications",
    label: "Certifications",
    fields: [
      { key: "name", label: "Certification", placeholder: "e.g. AWS Certified Developer" },
      { key: "issuer", label: "Issuer", placeholder: "Issuing body" },
      { key: "year", label: "Year", placeholder: "e.g. 2025" },
    ],
    empty: { name: "", issuer: "", year: "" },
  },
  {
    key: "publications",
    label: "Publications",
    fields: [
      { key: "title", label: "Title", placeholder: "Paper / article title", full: true },
      { key: "publisher", label: "Publisher / venue", placeholder: "Where it was published" },
      { key: "year", label: "Year", placeholder: "e.g. 2025" },
    ],
    empty: { title: "", publisher: "", year: "" },
  },
];

type ListSectionDef = { key: string; label: string; placeholder: string };

const LIST_SECTIONS: ListSectionDef[] = [
  { key: "skills", label: "Skills", placeholder: "e.g. Python, React, PostgreSQL" },
  { key: "languages", label: "Languages", placeholder: "e.g. English, Urdu" },
  { key: "interests", label: "Interests", placeholder: "e.g. AI research, open source" },
];

const STEP_LABELS = ["Upload CV", "Confirm details", "Submit"];

const inputClass =
  "w-full border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500";

function FieldLabel({ htmlFor, children }: { htmlFor: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-zinc-700">
      {children}
    </label>
  );
}

function StepIndicator({ current }: { current: number }) {
  return (
    <ol className="flex items-center gap-2">
      {STEP_LABELS.map((label, index) => (
        <li key={label} className="flex items-center gap-2">
          <span
            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
              index < current
                ? "bg-emerald-500 text-white"
                : index === current
                  ? "bg-violet-600 text-white"
                  : "border border-zinc-300 bg-white text-zinc-400"
            }`}
          >
            {index < current ? (
              <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-8 8a1 1 0 0 1-1.4 0l-4-4a1 1 0 1 1 1.4-1.4L8 12.6l7.3-7.3a1 1 0 0 1 1.4 0Z" clipRule="evenodd" />
              </svg>
            ) : (
              index + 1
            )}
          </span>
          <span
            className={`text-xs font-medium ${
              index === current ? "text-zinc-900" : "text-zinc-400"
            }`}
          >
            {label}
          </span>
          {index < STEP_LABELS.length - 1 ? (
            <span className="mx-1 h-px w-4 bg-zinc-300" />
          ) : null}
        </li>
      ))}
    </ol>
  );
}

function PlusIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14m-7-7h14" />
    </svg>
  );
}

function RemoveIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function ProcessingPanel({ status }: { status: "extracting" | "processing" }) {
  const isExtracting = status === "extracting";
  return (
    <div className="flex flex-col items-center py-10">
      <div className="flex gap-3">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="step-pulse h-2.5 w-2.5 rounded-full bg-violet-600"
            style={delay ? { animationDelay: `${delay}ms` } : undefined}
          />
        ))}
      </div>
      <h3 className="mt-5 text-lg font-semibold text-zinc-900">
        {isExtracting ? "Reading your CV…" : "We're processing your application"}
      </h3>
      <p className="mt-1 text-sm text-zinc-500">
        {isExtracting
          ? "AI is extracting your full CV (contact, skills, education, experience, projects, certifications). It usually takes a few seconds."
          : "This usually takes a few seconds."}
      </p>
    </div>
  );
}

function toStringList(raw?: unknown[]): string[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((s) => String(s)).filter((s) => s.trim() !== "");
}

function toObjectList(raw: unknown[] | undefined, keys: string[] = []): Record<string, string>[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    const item = typeof entry === "string" ? {} : (entry as Record<string, unknown>);
    return keys.reduce<Record<string, string>>((acc, key) => {
      const value = item?.[key];
      acc[key] = value === undefined || value === null ? "" : String(value);
      return acc;
    }, {});
  });
}

function parseChips(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

const INITIAL_OBJECT_SECTIONS = OBJECT_SECTIONS.reduce<Record<string, Record<string, string>[]>>(
  (acc, def) => {
    acc[def.key] = [];
    return acc;
  },
  {}
);

const INITIAL_LIST_SECTIONS = LIST_SECTIONS.reduce<Record<string, string[]>>((acc, def) => {
  acc[def.key] = [];
  return acc;
}, {});

export default function ApplyForm({
  jobId,
  jobTitle,
}: {
  jobId: string;
  jobTitle: string;
}) {
  const [step, setStep] = useState(0);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [state, setState] = useState<ApplyState>({ status: "idle" });

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [expectedSalary, setExpectedSalary] = useState("");
  const [address, setAddress] = useState("");
  const [summary, setSummary] = useState("");
  const [listSections, setListSections] =
    useState<Record<string, string[]>>(INITIAL_LIST_SECTIONS);
  const [objectSections, setObjectSections] =
    useState<Record<string, Record<string, string>[]>>(INITIAL_OBJECT_SECTIONS);
  const [consent, setConsent] = useState(false);

  function setProfileReset() {
    setFullName("");
    setEmail("");
    setPhone("");
    setExpectedSalary("");
    setAddress("");
    setSummary("");
    setListSections(INITIAL_LIST_SECTIONS);
    setObjectSections(INITIAL_OBJECT_SECTIONS);
  }

  function updateObject(sectionKey: string, index: number, field: string, value: string) {
    setObjectSections((prev) => ({
      ...prev,
      [sectionKey]: prev[sectionKey].map((item, i) =>
        i === index ? { ...item, [field]: value } : item
      ),
    }));
  }

  function addObjectSection(sectionKey: string) {
    const def = OBJECT_SECTIONS.find((d) => d.key === sectionKey);
    if (!def) return;
    setObjectSections((prev) => ({
      ...prev,
      [sectionKey]: [...prev[sectionKey], { ...def.empty }],
    }));
  }

  function removeObjectSection(sectionKey: string, index: number) {
    setObjectSections((prev) => ({
      ...prev,
      [sectionKey]: prev[sectionKey].filter((_, i) => i !== index),
    }));
  }

  function updateList(sectionKey: string, text: string) {
    setListSections((prev) => ({ ...prev, [sectionKey]: parseChips(text) }));
  }

  async function onFileChange(file: File | null) {
    setCvFile(file);
    if (!file) return;
    setState({ status: "extracting", error: undefined });
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API_BASE}/public/cv/extract`, {
        method: "POST",
        body,
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail =
          typeof data?.detail === "string"
            ? data.detail
            : Array.isArray(data?.detail) && typeof data.detail[0]?.msg === "string"
              ? data.detail[0].msg
              : `Could not read your CV (${res.status})`;
        setState({ status: "idle", error: detail });
        return;
      }
      const p: ExtractedProfile = data?.profile ?? {};
      setFullName(p.name ?? "");
      setEmail(p.email ?? "");
      setPhone(p.phone ?? "");
      setAddress(p.address ?? "");
      setExpectedSalary(p.expected_salary ?? "");
      setSummary(p.summary ?? "");
      setListSections({
        skills: toStringList(p.skills),
        languages: toStringList(p.languages),
        interests: toStringList(p.interests),
      });
      setObjectSections({
        education: toObjectList(p.education, ["degree", "institution", "years"]),
        experience: toObjectList(p.experience, ["position", "company", "years", "description"]),
        projects: toObjectList(p.projects, ["name", "link", "description"]),
        certifications: toObjectList(p.certifications, ["name", "issuer", "year"]),
        publications: toObjectList(p.publications, ["title", "publisher", "year"]),
      });
      setState({ status: "idle" });
      setStep(1);
    } catch {
      setState({
        status: "idle",
        error:
          "We couldn't read your CV right now. Please fill in the form manually and try again.",
      });
    }
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cvFile) return;
    setState({ status: "processing", error: undefined });

    const body = new FormData();
    body.append("file", cvFile);
    body.append("full_name", fullName.trim());
    body.append("email", email.trim());
    body.append("phone", phone.trim());
    body.append("expected_salary", expectedSalary.trim());
    body.append("address", address.trim());
    body.append("summary", summary.trim());
    body.append("skills", listSections.skills.join(", "));
    body.append("languages", listSections.languages.join(", "));
    body.append("interests", listSections.interests.join(", "));
    for (const def of OBJECT_SECTIONS) {
      body.append(def.key, JSON.stringify(objectSections[def.key]));
    }
    body.append("consent", consent ? "true" : "false");
    body.append(
      "profile_data",
      JSON.stringify({
        name: fullName.trim(),
        email: email.trim(),
        phone: phone.trim(),
        address: address.trim(),
        expected_salary: expectedSalary.trim(),
        summary: summary.trim(),
        ...LIST_SECTIONS.reduce<Record<string, string[]>>((acc, def) => {
          acc[def.key] = listSections[def.key];
          return acc;
        }, {}),
        ...OBJECT_SECTIONS.reduce<Record<string, Record<string, string>[]>>(
          (acc, def) => {
            acc[def.key] = objectSections[def.key];
            return acc;
          },
          {}
        ),
      })
    );

    try {
      const res = await fetch(`${API_BASE}/public/jobs/${jobId}/apply`, {
        method: "POST",
        body,
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail =
          typeof data?.detail === "string"
            ? data.detail
            : Array.isArray(data?.detail) && typeof data.detail[0]?.msg === "string"
              ? data.detail[0].msg
              : `Request failed (${res.status})`;
        setState({ status: "idle", error: detail });
        return;
      }
      const token = String(data.trackingUrl ?? "").split("/").pop();
      setState({
        status: "idle",
        success: {
          applicationId: data.applicationId,
          trackingToken: token || "",
        },
      });
    } catch {
      setState({
        status: "idle",
        error: "We couldn't submit your application. Please check your connection and try again.",
      });
    }
  }

  if (state.status === "extracting" || state.status === "processing") {
    return <ProcessingPanel status={state.status} />;
  }

  if (state.success) {
    return (
      <div className="flex flex-col items-center border border-emerald-200 bg-emerald-50/50 px-6 py-10 text-center">
        <span className="flex h-12 w-12 items-center justify-center bg-emerald-500 text-white">
          <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
        </span>
        <h3 className="mt-4 text-xl font-bold text-zinc-900">
          Application submitted successfully
        </h3>
        <p className="mt-1 text-sm text-zinc-600">
          Thank you for applying for {jobTitle}. Your application is now being
          processed.
        </p>
        <p className="mt-4 text-sm text-zinc-500">
          Application ID{" "}
          <span className="font-mono font-semibold text-zinc-900">
            {state.success.applicationId}
          </span>
        </p>
        <Link
          href={`/track/${state.success.trackingToken}`}
          className="mt-5 inline-flex items-center bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700"
        >
          Track my application
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <StepIndicator current={step} />

      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        {step === 0 ? (
          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
              Upload your CV
            </legend>
            <p className="text-sm text-zinc-600">
              We&apos;ll automatically read your full CV and build the
              application form for you — simply confirm the details.
            </p>
            <FileUpload
              name="file"
              maxSizeMb={10}
              onClearError={() => setState({ ...state, error: undefined })}
              onFileChange={onFileChange}
            />
            {state.error ? (
              <p className="border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {state.error}
              </p>
            ) : null}
            {cvFile ? (
              <button
                type="button"
                onClick={() => {
                  setState({ status: "idle", error: undefined });
                  setStep(1);
                }}
                className="inline-flex w-fit items-center text-sm font-medium text-violet-600 hover:text-violet-800"
              >
                Or enter your details manually
              </button>
            ) : null}
          </fieldset>
        ) : null}

        {step === 1 ? (
          <fieldset className="flex flex-col gap-4">
            <legend className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
              Confirm your details
            </legend>
            <p className="-mt-2 text-sm text-zinc-500">
              These were read from your CV. Correct anything that is wrong
              before continuing.
            </p>
            <div>
              <FieldLabel htmlFor="full_name">Full name *</FieldLabel>
              <input
                id="full_name"
                name="full_name"
                required
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <FieldLabel htmlFor="email">Email *</FieldLabel>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className={inputClass}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <FieldLabel htmlFor="phone">Phone</FieldLabel>
                <input
                  id="phone"
                  name="phone"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <FieldLabel htmlFor="expected_salary">Expected salary (PKR)</FieldLabel>
                <input
                  id="expected_salary"
                  name="expected_salary"
                  type="number"
                  min="0"
                  step="0.01"
                  value={expectedSalary}
                  onChange={(event) => setExpectedSalary(event.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
            <div>
              <FieldLabel htmlFor="address">Address</FieldLabel>
              <input
                id="address"
                name="address"
                value={address}
                onChange={(event) => setAddress(event.target.value)}
                className={inputClass}
              />
            </div>

            {summary ? (
              <div>
                <FieldLabel htmlFor="summary">Professional summary</FieldLabel>
                <textarea
                  id="summary"
                  name="summary"
                  rows={3}
                  value={summary}
                  onChange={(event) => setSummary(event.target.value)}
                  className={inputClass}
                />
              </div>
            ) : null}

            {OBJECT_SECTIONS.map((def) => {
              const items = objectSections[def.key];
              if (items.length === 0) return null;
              return (
                <div key={def.key} className="flex flex-col gap-2">
                  <p className="text-sm font-medium text-zinc-700">{def.label}</p>
                  {items.map((entry, index) => (
                    <div
                      key={index}
                      className="grid gap-2 border border-zinc-200 bg-zinc-50/50 p-3 sm:grid-cols-3"
                    >
                      {def.fields.map((field) => (
                        <div
                          key={field.key}
                          className={field.full ? "sm:col-span-3" : "sm:col-span-1"}
                        >
                          <label
                            className="mb-1 block text-xs text-zinc-500"
                            htmlFor={`${def.key}_${index}_${field.key}`}
                          >
                            {field.label}
                          </label>
                          {field.full ? (
                            <textarea
                              id={`${def.key}_${index}_${field.key}`}
                              rows={2}
                              value={entry[field.key]}
                              placeholder={field.placeholder}
                              onChange={(e) =>
                                updateObject(def.key, index, field.key, e.target.value)
                              }
                              className={inputClass}
                            />
                          ) : (
                            <input
                              id={`${def.key}_${index}_${field.key}`}
                              value={entry[field.key]}
                              placeholder={field.placeholder}
                              onChange={(e) =>
                                updateObject(def.key, index, field.key, e.target.value)
                              }
                              className={inputClass}
                            />
                          )}
                        </div>
                      ))}
                      <button
                        type="button"
                        aria-label={`Remove ${def.label} entry`}
                        onClick={() => removeObjectSection(def.key, index)}
                        className="justify-self-end p-2 text-zinc-400 hover:text-rose-600 sm:col-span-3"
                      >
                        <RemoveIcon />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => addObjectSection(def.key)}
                    className="inline-flex w-fit items-center gap-1 text-sm font-medium text-violet-600 hover:text-violet-800"
                  >
                    <PlusIcon />
                    Add {def.label.toLowerCase()}
                  </button>
                </div>
              );
            })}

            {LIST_SECTIONS.map((def) => (
              <div key={def.key}>
                <FieldLabel htmlFor={def.key}>{def.label}</FieldLabel>
                {def.key === "skills" ? (
                  <textarea
                    id={def.key}
                    name={def.key}
                    rows={2}
                    value={listSections[def.key].join(", ")}
                    placeholder={def.placeholder}
                    onChange={(event) => updateList(def.key, event.target.value)}
                    className={inputClass}
                  />
                ) : (
                  <input
                    id={def.key}
                    name={def.key}
                    value={listSections[def.key].join(", ")}
                    placeholder={def.placeholder}
                    onChange={(event) => updateList(def.key, event.target.value)}
                    className={inputClass}
                  />
                )}
              </div>
            ))}

            {OBJECT_SECTIONS.some((def) => objectSections[def.key].length > 0) ? (
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {OBJECT_SECTIONS.filter((def) => objectSections[def.key].length === 0).map(
                  (def) => (
                    <button
                      key={def.key}
                      type="button"
                      onClick={() => addObjectSection(def.key)}
                      className="inline-flex items-center gap-1 text-sm font-medium text-violet-600 hover:text-violet-800"
                    >
                      <PlusIcon />
                      Add {def.label.toLowerCase()}
                    </button>
                  )
                )}
              </div>
            ) : null}

            <div className="flex items-center justify-between pt-2">
              <span className="text-sm text-zinc-500">
                CV: <span className="font-medium text-zinc-800">{cvFile?.name}</span>{" "}
                <button
                  type="button"
                  onClick={() => {
                    setStep(0);
                    setCvFile(null);
                    setProfileReset();
                  }}
                  className="font-medium text-violet-600 hover:text-violet-800"
                >
                  Change
                </button>
              </span>
              <button
                type="button"
                onClick={() => setStep(2)}
                disabled={!fullName.trim() || !email.trim()}
                className="inline-flex items-center bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700 disabled:opacity-60"
              >
                Continue
              </button>
            </div>
          </fieldset>
        ) : null}

        {step === 2 ? (
          <fieldset className="flex flex-col gap-4">
            <legend className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
              Confirm and submit
            </legend>

            <dl className="divide-y divide-zinc-200 border border-zinc-200 bg-zinc-50/50">
              {(() => {
                const rows: { label: string; value: string }[] = [
                  { label: "Name", value: fullName },
                  { label: "Email", value: email },
                  { label: "Phone", value: phone },
                  { label: "Expected salary", value: expectedSalary },
                  { label: "Address", value: address },
                ];
                if (summary.trim()) {
                  rows.push({ label: "Professional summary", value: summary });
                }
                for (const def of OBJECT_SECTIONS) {
                  const items = objectSections[def.key].filter((entry) =>
                    Object.values(entry).some((v) => v.trim() !== "")
                  );
                  if (items.length === 0) continue;
                  rows.push({
                    label: def.label,
                    value: items
                      .map((entry) =>
                        Object.values(entry).filter((v) => v.trim() !== "").join(" · ")
                      )
                      .join("; "),
                  });
                }
                for (const def of LIST_SECTIONS) {
                  if (listSections[def.key].length === 0) continue;
                  rows.push({ label: def.label, value: listSections[def.key].join(", ") });
                }
                rows.push({ label: "CV", value: cvFile?.name ?? "" });
                return rows;
              })().map((row) => (
                <div key={row.label} className="flex justify-between gap-6 px-4 py-2.5 text-sm">
                  <dt className="text-zinc-500">{row.label}</dt>
                  <dd className="text-right text-zinc-900">{row.value || "—"}</dd>
                </div>
              ))}
            </dl>

            <label className="flex items-start gap-2 text-sm text-zinc-600">
              <input
                type="checkbox"
                name="consent"
                required
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
                className="mt-0.5 h-4 w-4 border-zinc-300 text-violet-600 focus:ring-violet-500"
              />
              <span>
                I consent to my application for {jobTitle} and my personal data
                being processed for recruitment purposes by HR OS. *
              </span>
            </label>

            {state.error ? (
              <p className="border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {state.error}
              </p>
            ) : null}

            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-sm font-medium text-zinc-500 hover:text-zinc-800"
              >
                ← Back to details
              </button>
              <button
                type="submit"
                disabled={state.status === "submitting" || !consent}
                className="inline-flex w-auto items-center justify-center bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700 disabled:opacity-60"
              >
                {state.status === "submitting" ? "Submitting…" : "Submit application"}
              </button>
            </div>
          </fieldset>
        ) : null}
      </form>
    </div>
  );
}