"use client";

import { useEffect, useState } from "react";

import Modal from "@/app/hr/_components/Modal";
import Button from "@/app/hr/_components/Button";
import { API_BASE, getToken } from "@/app/hr/_lib/api";

function CvViewer({
  cvId,
  fileName,
  mimeType,
}: {
  cvId: string;
  fileName: string;
  mimeType: string | null;
}) {
  const [readyUrl, setReadyUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const token = getToken();
    const src = `${API_BASE}/applications/cv/${cvId}/file`;

    fetch(src, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (cancelled) return;
        if (!res.ok) {
          throw new Error(`Failed to load CV (${res.status})`);
        }
        return res.blob();
      })
      .then((blob) => {
        if (cancelled || !blob) return;
        setReadyUrl(URL.createObjectURL(blob));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load CV");
      });

    return () => {
      cancelled = true;
      setReadyUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [cvId]);

  const loading = readyUrl === null && error === null;
  const lowerName = fileName.toLowerCase();
  const isPdf =
    mimeType === "application/pdf" || lowerName.endsWith(".pdf");
  const isImage = mimeType?.startsWith("image/") ?? false;
  const isText =
    mimeType === "text/plain" ||
    mimeType?.startsWith("text/") ||
    lowerName.endsWith(".txt");
  const embeddable = isPdf || isImage || isText;

  const download = () => {
    if (!readyUrl) return;
    const a = document.createElement("a");
    a.href = readyUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <p className="min-w-0 truncate text-sm font-medium text-zinc-900">
          {fileName}
        </p>
        {readyUrl ? (
          <div className="flex shrink-0 gap-2">
            <Button
              variant="secondary"
              onClick={() => window.open(readyUrl, "_blank")}
            >
              Open in new tab
            </Button>
            <Button onClick={download}>Download</Button>
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="flex flex-col items-center gap-2 border border-zinc-200 bg-white py-16 text-sm text-zinc-500">
          <span className="h-6 w-6 animate-spin rounded-full border-2 border-violet-600 border-t-transparent" />
          Loading CV…
        </div>
      ) : null}

      {error ? (
        <div className="flex flex-col items-center gap-3 border border-dashed border-zinc-300 bg-rose-50/50 px-6 py-14 text-center">
          <p className="text-sm text-rose-700">{error}</p>
        </div>
      ) : null}

      {readyUrl ? (
        embeddable ? (
          <iframe
            src={readyUrl}
            title={fileName}
            className="h-[60vh] w-full border border-zinc-200 bg-white"
          />
        ) : (
          <div className="flex flex-col items-center gap-3 border border-dashed border-zinc-300 bg-violet-50/50 px-6 py-14 text-center">
            <p className="text-sm text-zinc-500">
              This file type cannot be previewed inline.
            </p>
            <Button onClick={download}>Download {fileName}</Button>
          </div>
        )
      ) : null}
    </div>
  );
}

export default function CvPreview({
  open,
  onClose,
  cvId,
  fileName,
  mimeType,
}: {
  open: boolean;
  onClose: () => void;
  cvId: string | null;
  fileName: string;
  mimeType: string | null;
}) {
  if (!open || !cvId) return null;

  return (
    <Modal open={open} onClose={onClose} title="CV preview">
      <CvViewer
        key={cvId}
        cvId={cvId}
        fileName={fileName}
        mimeType={mimeType}
      />
    </Modal>
  );
}
