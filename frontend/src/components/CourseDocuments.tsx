"use client";

import React, { useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  FileQuestion,
  Loader2,
  Presentation,
  RotateCcw,
  ScrollText,
  Upload,
  X,
  type LucideIcon,
} from "lucide-react";
import { apiRequest } from "@/lib/api";

export interface DocumentItem {
  id: string;
  title: string;
  kind: string;
  year?: number;
  status: string;
  contentSnippet?: string;
}

type Kind = "syllabus" | "notes" | "slides" | "past_paper" | "model_paper" | "rubric";

const CATEGORIES: { kind: Kind; label: string; hint: string; icon: LucideIcon; dated?: boolean }[] = [
  { kind: "syllabus", label: "Syllabus", hint: "Module outline and learning outcomes", icon: ScrollText },
  { kind: "notes", label: "Lecture Notes", hint: "Handouts and reading notes", icon: BookOpen },
  { kind: "slides", label: "Lecture Slides", hint: "PowerPoint or PDF slide decks", icon: Presentation },
  { kind: "past_paper", label: "Past Papers", hint: "Earlier exams, checked for repeated questions", icon: FileText, dated: true },
  { kind: "model_paper", label: "Model Papers", hint: "Sample and specimen papers", icon: FileQuestion, dated: true },
  { kind: "rubric", label: "Rubrics", hint: "Marking schemes and criteria", icon: ClipboardCheck },
];

// Kinds no longer offered for upload, still shown for documents already stored.
const LEGACY_LABELS: Record<string, string> = { qa_manual: "QA Manual" };

const ACCEPT = ".pdf,.docx,.pptx,.md,.txt";
const ACCEPTED_EXT = ACCEPT.split(",");
const THIS_YEAR = String(new Date().getFullYear());

const isDated = (kind: string) => CATEGORIES.some((c) => c.kind === kind && c.dated);
const labelOf = (kind: string) => CATEGORIES.find((c) => c.kind === kind)?.label ?? LEGACY_LABELS[kind] ?? kind.replace(/_/g, " ");

interface QueuedFile {
  key: string;
  file: File;
  kind: Kind;
  year: string;
  status: "ready" | "uploading" | "done" | "failed";
  error?: string;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const SELECT =
  "text-xs rounded-lg bg-white border border-slate-200 px-2 py-1.5 text-slate-800 focus:outline-none focus:border-emerald-600 shadow-xs disabled:bg-slate-50 disabled:text-slate-500";

export function CourseDocuments({
  courseCode,
  documents,
  onUploaded,
}: {
  courseCode: string;
  documents: DocumentItem[];
  onUploaded: (doc: DocumentItem) => void;
}) {
  const [category, setCategory] = useState<Kind>("syllabus");
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState<{ ok: boolean; text: string } | null>(null);
  const [rejected, setRejected] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const countByKind = useMemo(() => {
    const out: Record<string, number> = {};
    for (const d of documents) out[d.kind] = (out[d.kind] || 0) + 1;
    return out;
  }, [documents]);

  const groups = useMemo(() => {
    const order = [...CATEGORIES.map((c) => c.kind as string), ...Object.keys(countByKind).filter((k) => !CATEGORIES.some((c) => c.kind === k))];
    return order
      .map((kind) => ({ kind, docs: documents.filter((d) => d.kind === kind) }))
      .filter((g) => g.docs.length > 0);
  }, [documents, countByKind]);

  const addFiles = (files: FileList | File[]) => {
    const accepted: QueuedFile[] = [];
    const skipped: string[] = [];
    for (const file of Array.from(files)) {
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      if (!ACCEPTED_EXT.includes(ext)) {
        skipped.push(file.name);
        continue;
      }
      accepted.push({
        key: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`,
        file,
        kind: category,
        year: THIS_YEAR,
        status: "ready",
      });
    }
    setRejected(skipped);
    setSummary(null);
    setQueue((q) => [...q.filter((f) => f.status !== "done"), ...accepted]);
  };

  const update = (key: string, patch: Partial<QueuedFile>) =>
    setQueue((q) => q.map((f) => (f.key === key ? { ...f, ...patch } : f)));

  const pending = queue.filter((f) => f.status === "ready" || f.status === "failed");

  const uploadAll = async () => {
    setUploading(true);
    setSummary(null);
    let ok = 0;
    let failed = 0;
    // One request per file, in order, so each row reports its own result.
    for (const item of pending) {
      update(item.key, { status: "uploading", error: undefined });
      try {
        const form = new FormData();
        form.append("file", item.file);
        form.append("kind", item.kind);
        if (isDated(item.kind) && item.year) form.append("year", item.year);
        const doc = await apiRequest<DocumentItem>(`/courses/${courseCode}/documents`, { method: "POST", body: form });
        onUploaded(doc);
        update(item.key, { status: "done" });
        ok += 1;
      } catch (err) {
        update(item.key, { status: "failed", error: ((err as Error)?.message || "Upload failed").replace(/^API Error \(\d+\): /, "") });
        failed += 1;
      }
    }
    setUploading(false);
    setSummary({
      ok: failed === 0,
      text: failed
        ? `${ok} of ${ok + failed} files indexed. Fix or remove the failed ones and try again.`
        : `${ok} ${ok === 1 ? "file" : "files"} parsed and indexed into the knowledge base.`,
    });
  };

  const active = CATEGORIES.find((c) => c.kind === category)!;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Upload className="w-4 h-4 text-emerald-600" aria-hidden />
            Upload course materials
          </h3>
          <p className="text-[11px] text-slate-500 mt-1">
            Pick a category, then add as many files as you need. You can change the category of each file before uploading.
          </p>
        </div>

        {/* Category picker */}
        <div role="radiogroup" aria-label="Document category" className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {CATEGORIES.map((c) => {
            const Icon = c.icon;
            const selected = c.kind === category;
            return (
              <button
                key={c.kind}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setCategory(c.kind)}
                className={`flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-colors cursor-pointer ${
                  selected ? "border-emerald-600 bg-emerald-50/70 ring-1 ring-emerald-600" : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <span
                  className={`w-8 h-8 shrink-0 rounded-lg flex items-center justify-center ${
                    selected ? "bg-emerald-700 text-white" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  <Icon className="w-4 h-4" aria-hidden />
                </span>
                <span className="min-w-0">
                  <span className="block text-xs font-semibold text-slate-900 truncate">{c.label}</span>
                  <span className="block text-[11px] text-slate-500">
                    {countByKind[c.kind] ? `${countByKind[c.kind]} uploaded` : "None yet"}
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
          }}
          className={`rounded-xl border-2 border-dashed px-4 py-6 text-center transition-colors ${
            dragging ? "border-emerald-600 bg-emerald-50" : "border-slate-200 bg-slate-50/60"
          }`}
        >
          <Upload className={`w-6 h-6 mx-auto mb-2 ${dragging ? "text-emerald-700" : "text-slate-400"}`} aria-hidden />
          <p className="text-xs text-slate-700">
            Drop <strong>{active.label.toLowerCase()}</strong> here, or{" "}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="font-semibold text-emerald-700 hover:underline cursor-pointer"
            >
              browse files
            </button>
          </p>
          <p className="text-[11px] text-slate-500 mt-1">{active.hint}. PDF, DOCX, PPTX, MD or TXT; select several at once.</p>
          <input
            ref={inputRef}
            id="upload-doc-file-input"
            type="file"
            multiple
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) addFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </div>

        {rejected.length > 0 && (
          <p role="alert" className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            Skipped {rejected.length === 1 ? "an unsupported file" : `${rejected.length} unsupported files`}: {rejected.join(", ")}
          </p>
        )}

        {/* Queue */}
        {queue.length > 0 && (
          <div className="rounded-lg border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
              <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                {pending.length ? `${pending.length} ${pending.length === 1 ? "file" : "files"} to upload` : "Upload complete"}
              </span>
              <button
                type="button"
                disabled={uploading}
                onClick={() => {
                  setQueue([]);
                  setSummary(null);
                }}
                className="text-[11px] font-semibold text-slate-500 hover:text-slate-800 disabled:opacity-50 cursor-pointer"
              >
                Clear list
              </button>
            </div>
            <ul className="divide-y divide-slate-100">
              {queue.map((f) => {
                const locked = uploading || f.status === "done" || f.status === "uploading";
                return (
                  <li key={f.key} className="px-3 py-2.5 flex flex-wrap items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400 shrink-0" aria-hidden />
                    <div className="min-w-0 flex-1 basis-40">
                      <div className="text-xs font-semibold text-slate-900 truncate" title={f.file.name}>
                        {f.file.name}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {formatSize(f.file.size)}
                        {f.status === "failed" && f.error && <span className="text-rose-700"> · {f.error}</span>}
                      </div>
                    </div>
                    <select
                      aria-label={`Category for ${f.file.name}`}
                      value={f.kind}
                      disabled={locked}
                      onChange={(e) => update(f.key, { kind: e.target.value as Kind })}
                      className={SELECT}
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c.kind} value={c.kind}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                    {isDated(f.kind) && (
                      <input
                        aria-label={`Year for ${f.file.name}`}
                        type="number"
                        min={1990}
                        max={2100}
                        value={f.year}
                        disabled={locked}
                        onChange={(e) => update(f.key, { year: e.target.value })}
                        className={`${SELECT} w-20`}
                      />
                    )}
                    <span className="w-20 text-right text-[11px] font-semibold">
                      {f.status === "uploading" ? (
                        <span className="inline-flex items-center gap-1 text-slate-600">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden /> Indexing
                        </span>
                      ) : f.status === "done" ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700">
                          <CheckCircle2 className="w-3.5 h-3.5" aria-hidden /> Indexed
                        </span>
                      ) : f.status === "failed" ? (
                        <span className="inline-flex items-center gap-1 text-rose-700">
                          <AlertCircle className="w-3.5 h-3.5" aria-hidden /> Failed
                        </span>
                      ) : (
                        <span className="text-slate-500">Ready</span>
                      )}
                    </span>
                    <button
                      type="button"
                      aria-label={`Remove ${f.file.name}`}
                      disabled={locked}
                      onClick={() => setQueue((q) => q.filter((x) => x.key !== f.key))}
                      className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:invisible cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] text-slate-500">Scanned PDFs are read with Document AI OCR.</span>
          <button
            id="upload-submit-btn"
            type="button"
            onClick={uploadAll}
            disabled={pending.length === 0 || uploading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white font-semibold text-xs transition-all shadow-xs cursor-pointer"
          >
            {uploading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden />
            ) : queue.some((f) => f.status === "failed") ? (
              <RotateCcw className="w-3.5 h-3.5" aria-hidden />
            ) : (
              <Upload className="w-3.5 h-3.5" aria-hidden />
            )}
            {uploading
              ? "Uploading…"
              : pending.length > 1
              ? `Upload & index ${pending.length} files`
              : "Upload & index"}
          </button>
        </div>

        {summary && (
          <div
            role="status"
            className={`p-2.5 rounded-lg border text-xs flex items-center gap-2 ${
              summary.ok ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-amber-50 border-amber-200 text-amber-900"
            }`}
          >
            {summary.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-hidden /> : <AlertCircle className="w-4 h-4" aria-hidden />}
            <span>{summary.text}</span>
          </div>
        )}
      </div>

      {/* Archive grouped by category */}
      <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Indexed course archive</h3>
          <span className="text-[11px] text-slate-500">
            {documents.length} {documents.length === 1 ? "document" : "documents"}
          </span>
        </div>
        {groups.length === 0 ? (
          <p className="text-xs text-slate-500">Nothing uploaded yet. Start with the syllabus, then add notes, slides and papers.</p>
        ) : (
          groups.map(({ kind, docs }) => (
            <section key={kind} className="space-y-2">
              <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {labelOf(kind)} <span className="font-mono text-slate-400">({docs.length})</span>
              </h4>
              <ul className="space-y-1.5">
                {docs.map((doc) => (
                  <li key={doc.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-4 h-4 text-emerald-600 shrink-0" aria-hidden />
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-slate-900 truncate" title={doc.title}>
                          {doc.title}
                        </div>
                        {doc.year && <div className="text-[11px] text-slate-500">Year {doc.year}</div>}
                      </div>
                    </div>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                      {doc.status}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))
        )}
      </div>
    </div>
  );
}
