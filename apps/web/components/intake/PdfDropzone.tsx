"use client";

import { useDropzone } from "react-dropzone";
import { FileText, Upload } from "lucide-react";
import { cn } from "@/lib/utils";

export function PdfDropzone({
  label,
  file,
  onFile,
}: {
  label: string;
  file?: File;
  onFile: (f: File) => void;
}) {
  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
    onDropAccepted: ([f]) => onFile(f),
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "cursor-pointer rounded-xl border-2 border-dashed border-[var(--color-line)] p-6 text-center transition-colors",
        isDragActive && "border-[var(--color-advocate)] bg-[var(--color-advocate)]/10",
        file && "border-solid border-[var(--color-admit)]/60 bg-[var(--color-admit)]/5"
      )}
    >
      <input {...getInputProps()} aria-label={label} />
      {file ? (
        <FileText className="mx-auto h-8 w-8 text-[var(--color-admit)]" />
      ) : (
        <Upload className="mx-auto h-8 w-8 text-[var(--color-muted)]" />
      )}
      <p className="mt-2 text-sm text-[var(--color-ink)]">
        {file ? file.name : `Drop your ${label} (PDF)`}
      </p>
      {fileRejections.length > 0 && (
        <p className="mt-1 text-xs text-[var(--color-deny)]">PDF only, up to 10 MB.</p>
      )}
    </div>
  );
}
