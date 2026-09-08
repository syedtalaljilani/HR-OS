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
  education?: unknown[];
  experience?: unknown[];
  skills?: string[];
};

type EducationItem = { degree: string; institution: string; years: string };
type ExperienceItem = { position: string; company: string; years: string; description: string };

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
          ? "AI is extracting your details (name, email, phone, skills). It usually takes a few seconds."
          : "This usually takes a few seconds."}
      </p>
    </div>
  );
}

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
  const [skills, setSkills] = useState<string[]>([]);
  const [education, setEducation] = useState<EducationItem[]>([]);
  const [experience, setExperience] = useState<ExperienceItem[]>([]);
  const [consent, setConsent] = useState(false);

  const skillsText = skills.join(", ");

  function updateSkills(text: string) {
    setSkills(
      text
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    );
  }

  function updateEducation(index: number, field: keyof EducationItem, value: string) {
    setEducation((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  }

  function updateExperience(index: number, field: keyof ExperienceItem, value: string) {
    setExperience((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  }

  function setProfileReset() {
    setFullName("");
    setEmail("");
    setPhone("");
    setExpectedSalary("");
    setAddress("");
    setSkills([]);
    setEducation([]);
    setExperience([]);
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
      setSkills(Array.isArray(p.skills) ? p.skills.filter((s) => typeof s === "string") : []);
      setEducation(toEducationItems(p.education));
      setExperience(toExperienceItems(p.experience));
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
    body.append("skills", skillsText);
    body.append("education", JSON.stringify(education));
    body.append("experience", JSON.stringify(experience));
    body.append("consent", consent ? "true" : "false");

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

  function toEducationItems(raw?: unknown[]): EducationItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    const item =
      typeof entry === "string" ? {} : (entry as Record<string, unknown>);
    return {
      degree: item?.degree ? String(item.degree) : "",
      institution: item?.institution ? String(item.institution) : "",
      years: item?.years ? String(item.years) : "",
    };
  });
}

function toExperienceItems(raw?: unknown[]): ExperienceItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    const item =
      typeof entry === "string" ? {} : (entry as Record<string, unknown>);
    return {
      position: item?.position ? String(item.position) : "",
      company: item?.company ? String(item.company) : "",
      years: item?.years ? String(item.years) : "",
      description: item?.description ? String(item.description) : "",
    };
  });
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
              We&apos;ll automatically read your details from the CV and pre-fill
              the application form for you.
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
          </fieldset>
        ) : null}

        {step === 1 ? (
          <fieldset className="flex flex-col gap-4">
            <legend className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
              Confirm your details
            </legend>
            <p className="-mt-2 text-sm text-zinc-500">
              These were read from your CV. Please correct anything that is
              wrong before continuing.
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

            <div>
              <FieldLabel htmlFor="skills">Skills (comma-separated)</FieldLabel>
              <textarea
                id="skills"
                name="skills"
                rows={2}
                value={skillsText}
                onChange={(event) => updateSkills(event.target.value)}
                className={inputClass}
              />
            </div>

            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium text-zinc-700">Education</p>
              {education.map((entry, index) => (
                <div
                  key={index}
                  className="grid gap-2 border border-zinc-200 bg-zinc-50/50 p-3 sm:grid-cols-[2fr_2fr_1fr_auto]"
                >
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500" htmlFor={`edu_degree_${index}`}>
                      Degree
                    </label>
                    <input
                      id={`edu_degree_${index}`}
                      value={entry.degree}
                      onChange={(e) => updateEducation(index, "degree", e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500" htmlFor={`edu_institution_${index}`}>
                      Institution
                    </label>
                    <input
                      id={`edu_institution_${index}`}
                      value={entry.institution}
                      onChange={(e) => updateEducation(index, "institution", e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500" htmlFor={`edu_years_${index}`}>
                      Years
                    </label>
                    <input
                      id={`edu_years_${index}`}
                      value={entry.years}
                      onChange={(e) => updateEducation(index, "years", e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <button
                    type="button"
                    aria-label="Remove education entry"
                    onClick={() =>
                      setEducation((prev) => prev.filter((_, i) => i !== index))
                    }
                    className="self-end p-2 text-zinc-400 hover:text-rose-600"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() =>
                  setEducation((prev) => [
                    ...prev,
                    { degree: "", institution: "", years: "" },
                  ])
                }
                className="inline-flex w-fit items-center gap-1 text-sm font-medium text-violet-600 hover:text-violet-800"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14m-7-7h14" />
                </svg>
                Add education
              </button>
            </div>

            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium text-zinc-700">Work experience</p>
              {experience.map((entry, index) => (
                <div
                  key={index}
                  className="grid gap-2 border border-zinc-200 bg-zinc-50/50 p-3 sm:grid-cols-[2fr_2fr_1fr_auto]"
                >
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500" htmlFor={`exp_position_${index}`}>
                      Position
                    </label>
                    <input
                      id={`exp_position_${index}`}
                      value={entry.position}
                      onChange={(e) => updateExperience(index, "position", e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500" htmlFor={`exp_company_${index}`}>
                      Company
                    </label>
                    <input
                      id={`exp_company_${index}`}
                      value={entry.company}
                      onChange={(e) => updateExperience(index, "company", e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500" htmlFor={`exp_years_${index}`}>
                      Years
                    </label>
                    <input
                      id={`exp_years_${index}`}
                      value={entry.years}
                      onChange={(e) => updateExperience(index, "years", e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <button
                    type="button"
                    aria-label="Remove experience entry"
                    onClick={() =>
                      setExperience((prev) => prev.filter((_, i) => i !== index))
                    }
                    className="self-end p-2 text-zinc-400 hover:text-rose-600"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() =>
                  setExperience((prev) => [
                    ...prev,
                    { position: "", company: "", years: "", description: "" },
                  ])
                }
                className="inline-flex w-fit items-center gap-1 text-sm font-medium text-violet-600 hover:text-violet-800"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14m-7-7h14" />
                </svg>
                Add experience
              </button>
            </div>

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
              {[
                { label: "Name", value: fullName },
                { label: "Email", value: email },
                { label: "Phone", value: phone },
                { label: "Expected salary", value: expectedSalary },
                { label: "Address", value: address },
                { label: "Skills", value: skillsText },
                {
                  label: "Education",
                  value: education
                    .filter((e) => e.degree || e.institution)
                    .map((e) => [e.degree, e.institution, e.years].filter(Boolean).join(" · "))
                    .join("; "),
                },
                {
                  label: "Experience",
                  value: experience
                    .filter((e) => e.position || e.company)
                    .map((e) => [e.position, e.company, e.years].filter(Boolean).join(" · "))
                    .join("; "),
                },
                { label: "CV", value: cvFile?.name },
              ].map((row) => (
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