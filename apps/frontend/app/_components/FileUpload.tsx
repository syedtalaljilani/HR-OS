"use client";

import { useRef, useState } from "react";

export default function FileUpload({
  name,
  accept = ".pdf,.docx,.doc,.txt",
  maxSizeMb = 10,
  onClearError,
  onFileChange,
}: {
  name: string;
  accept?: string;
  maxSizeMb?: number;
  onClearError?: () => void;
  onFileChange?: (file: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [sizeError, setSizeError] = useState<string | null>(null);

  function select(next: FileList | null) {
    if (onClearError) onClearError();
    const candidate = next?.[0];
    if (!candidate) return;
    if (candidate.size > maxSizeMb * 1024 * 1024) {
      setFile(null);
      setSizeError(
        `That file is ${(candidate.size / (1024 * 1024)).toFixed(1)} MB. ` +
          `Please upload a file no larger than ${maxSizeMb} MB.`
      );
      if (inputRef.current) inputRef.current.value = "";
      onFileChange?.(null);
      return;
    }
    setSizeError(null);
    setFile(candidate);
    onFileChange?.(candidate);
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        id={name}
        name={name}
        type="file"
        accept={accept}
        required
        className="sr-only"
        onChange={(event) => select(event.target.files)}
      />
      {!file ? (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            select(event.dataTransfer.files);
          }}
          className={`flex w-full flex-col items-center justify-center gap-2 border border-dashed px-6 py-10 text-center transition ${
            dragOver
              ? "border-violet-500 bg-violet-50"
              : "border-zinc-300 bg-white hover:border-violet-400 hover:bg-violet-50/40"
          }`}
        >
          <span className="flex h-10 w-10 items-center justify-center bg-violet-50 text-violet-600">
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z"
              />
            </svg>
          </span>
          <span className="text-sm font-medium text-zinc-800">
            Drag & drop your CV here
          </span>
          <span className="text-sm text-zinc-500">
            or <span className="font-medium text-violet-600">browse</span> from
            your computer
          </span>
          <span className="text-xs text-zinc-400">PDF / DOCX / TXT</span>
        </button>
      ) : (
        <div className="flex items-center justify-between gap-3 border border-zinc-200 bg-violet-50/50 px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center bg-violet-600 text-white">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                />
              </svg>
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-zinc-900">
                {file.name}
              </p>
              <p className="text-xs text-zinc-500">
                {(file.size / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              if (onClearError) onClearError();
              setFile(null);
              if (inputRef.current) inputRef.current.value = "";
              onFileChange?.(null);
            }}
            className="shrink-0 text-sm font-medium text-violet-600 hover:text-violet-800"
          >
            Replace
          </button>
        </div>
      )}
      {sizeError ? (
        <p className="border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {sizeError}
        </p>
      ) : null}
      <p className="text-xs text-zinc-400">
        PDF, DOCX or TXT • Max {maxSizeMb} MB
      </p>
    </div>
  );
}