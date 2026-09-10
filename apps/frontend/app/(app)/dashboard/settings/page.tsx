"use client";

import { useEffect, useState } from "react";

import Button from "@/app/hr/_components/Button";
import { Field, inputClass } from "@/app/hr/_components/Field";
import LocationPicker from "@/app/hr/_components/LocationPicker";
import { ErrorNote } from "@/app/hr/_components/Modal";
import { api } from "@/app/hr/_lib/api";

type OrgSettings = {
  company_name: string;
  hr_name: string;
  company_location: string;
};

export default function SettingsPage() {
  const [companyName, setCompanyName] = useState("");
  const [hrName, setHrName] = useState("");
  const [companyLocation, setCompanyLocation] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const settings = await api<OrgSettings>("/settings/organization");
        setCompanyName(settings.company_name ?? "");
        setHrName(settings.hr_name ?? "");
        setCompanyLocation(settings.company_location ?? "");
        setError(null);
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Failed to load settings"
        );
      } finally {
        setLoading(false);
        setLoaded(true);
      }
    })();
  }, []);

  async function save() {
    setSaving(true);
    setNotice(null);
    try {
      await api<OrgSettings>("/settings/organization", {
        method: "PUT",
        body: {
          company_name: companyName,
          hr_name: hrName,
          company_location: companyLocation,
        },
      });
      setError(null);
      setNotice(
        "Saved. Email drafts will use this company, HR and location identity."
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not save settings"
      );
    } finally {
      setSaving(false);
    }
  }

  if (error && !loaded) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorNote message={error} />
      </div>
    );
  }
  if (loading || !loaded) {
    return (
      <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
        <div className="skeleton h-6 w-40" />
        <div className="skeleton h-3.5 w-72" />
        <div className="skeleton h-48 w-full max-w-xl" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6 sm:p-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
          Settings
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Organization identity used in email drafts (company name, HR
          sign-off and office location).
        </p>
      </div>

      <section className="max-w-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4">
          <Field
            label="Company name"
            hint="Appears in the email body, e.g. 'the Senior Engineer position at Acme Engineering'."
          >
            <input
              value={companyName}
              onChange={(event) => setCompanyName(event.target.value)}
              placeholder="e.g. Acme Engineering Pvt Ltd"
              className={inputClass()}
            />
          </Field>
          <Field
            label="HR name"
            hint="Used as the email sign-off, e.g. 'Best regards, Maria Khan'."
          >
            <input
              value={hrName}
              onChange={(event) => setHrName(event.target.value)}
              placeholder="e.g. Maria Khan"
              className={inputClass()}
            />
          </Field>
          <Field
            label="Company location"
            hint="Office address, included in onsite interview emails together with a map link. Type it below or set it by clicking the map."
          >
            <textarea
              rows={2}
              value={companyLocation}
              onChange={(event) => setCompanyLocation(event.target.value)}
              placeholder="e.g. 3rd Floor, Progressive Plaza, Blue Area, Islamabad"
              className={inputClass()}
            />
          </Field>
          <LocationPicker value={companyLocation} onChange={setCompanyLocation} />

          {error ? <ErrorNote message={error} /> : null}
          {notice ? (
            <p className="border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {notice}
            </p>
          ) : null}

          <div className="flex justify-end gap-2 pt-1">
            <Button
              onClick={save}
              loading={saving}
              disabled={
                !companyName.trim() && !hrName.trim() && !companyLocation.trim()
              }
            >
              Save settings
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}