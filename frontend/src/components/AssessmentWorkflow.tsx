"use client";

import React, { useEffect, useRef } from "react";
import { AlertTriangle, ArrowRight, Check, CheckCircle2, Info, X } from "lucide-react";

export type WorkflowTab = "blueprint" | "pool" | "review" | "solver" | "moderation" | "export";
export type StageState = "done" | "current" | "todo";

export interface StageDef {
  id: "author" | "verify" | "signoff";
  label: string;
  tabs: { id: WorkflowTab; label: string; badge?: React.ReactNode }[];
  state: StageState;
  summary: string;
}

export const WORKFLOW_TABS: WorkflowTab[] = ["blueprint", "pool", "review", "solver", "moderation", "export"];

/** Three lecturer-facing stages; the six agent steps live inside them as sub-tabs. */
export function StageNav({
  stages,
  activeTab,
  onSelect,
}: {
  stages: StageDef[];
  activeTab: WorkflowTab;
  onSelect: (tab: WorkflowTab) => void;
}) {
  const activeStage = stages.find((s) => s.tabs.some((t) => t.id === activeTab)) || stages[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6">
      <nav aria-label="Assessment workflow" className="grid grid-cols-3 gap-2 sm:gap-3 pt-3">
        {stages.map((stage, i) => {
          const isActive = stage.id === activeStage.id;
          return (
            <button
              key={stage.id}
              onClick={() => onSelect(stage.tabs[0].id)}
              aria-current={isActive ? "step" : undefined}
              className={`text-left rounded-lg border px-3 py-2.5 transition cursor-pointer ${
                isActive
                  ? "border-emerald-300 bg-emerald-50/70"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <span className="flex items-center gap-2">
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    stage.state === "done"
                      ? "bg-emerald-700 text-white"
                      : isActive
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 border border-slate-200"
                  }`}
                  aria-hidden
                >
                  {stage.state === "done" ? <Check className="w-3.5 h-3.5" /> : i + 1}
                </span>
                <span className="text-sm font-bold text-slate-900">{stage.label}</span>
              </span>
              <span
                className={`hidden sm:block text-xs mt-1 ml-8 ${
                  stage.state === "done" ? "text-emerald-700" : stage.state === "current" ? "text-amber-700" : "text-slate-500"
                }`}
              >
                {stage.summary}
              </span>
            </button>
          );
        })}
      </nav>

      <div role="tablist" aria-label={`${activeStage.label} steps`} className="flex gap-1 mt-2 overflow-x-auto">
        {activeStage.tabs.map((tab) => {
          const selected = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={selected}
              aria-controls="workflow-panel"
              onClick={() => onSelect(tab.id)}
              className={`px-3 py-2.5 text-sm font-medium border-b-2 flex items-center gap-2 whitespace-nowrap transition cursor-pointer ${
                selected
                  ? "text-emerald-800 border-emerald-700 font-semibold"
                  : "text-slate-600 border-transparent hover:text-slate-900"
              }`}
            >
              {tab.label}
              {tab.badge}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export interface NextAction {
  tone: "action" | "waiting" | "done";
  text: React.ReactNode;
  cta?: { label: string; onClick: () => void; disabled?: boolean };
}

/** The one thing the current user needs to do next, always visible under the stage nav. */
export function NextActionStrip({ action }: { action: NextAction }) {
  const tone =
    action.tone === "done"
      ? "bg-emerald-50 border-emerald-200 text-emerald-900"
      : action.tone === "waiting"
      ? "bg-sky-50 border-sky-200 text-sky-900"
      : "bg-amber-50 border-amber-200 text-amber-900";
  const Icon = action.tone === "done" ? CheckCircle2 : action.tone === "waiting" ? Info : AlertTriangle;

  return (
    <div className={`rounded-xl border px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3 ${tone}`}>
      <div className="flex items-start gap-2.5 flex-1">
        <Icon className="w-4 h-4 mt-0.5 shrink-0" aria-hidden />
        <p className="text-sm">
          <span className="font-semibold">Next: </span>
          {action.text}
        </p>
      </div>
      {action.cta && (
        <button
          onClick={action.cta.onClick}
          disabled={action.cta.disabled}
          className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-sm font-semibold flex items-center justify-center gap-1.5 whitespace-nowrap transition cursor-pointer disabled:opacity-50"
        >
          {action.cta.label}
          <ArrowRight className="w-4 h-4" aria-hidden />
        </button>
      )}
    </div>
  );
}

export interface Notice {
  id: number;
  kind: "success" | "error" | "info";
  text: string;
  undo?: () => void;
}

/** Inline status line replacing alert(): announced politely, errors assertively, optional Undo. */
export function NoticeToast({ notice, onDismiss }: { notice: Notice | null; onDismiss: () => void }) {
  return (
    <div aria-live="polite" className="fixed bottom-4 inset-x-4 sm:left-auto sm:right-6 sm:w-[420px] z-40 pointer-events-none">
      {notice && (
        <div
          role={notice.kind === "error" ? "alert" : "status"}
          className={`pointer-events-auto rounded-xl border shadow-lg px-4 py-3 flex items-start gap-3 bg-white ${
            notice.kind === "error" ? "border-rose-200" : "border-slate-200"
          }`}
        >
          {notice.kind === "error" ? (
            <AlertTriangle className="w-4 h-4 mt-0.5 text-rose-700 shrink-0" aria-hidden />
          ) : (
            <CheckCircle2 className="w-4 h-4 mt-0.5 text-emerald-700 shrink-0" aria-hidden />
          )}
          <p className={`text-sm flex-1 ${notice.kind === "error" ? "text-rose-800" : "text-slate-800"}`}>{notice.text}</p>
          {notice.undo && (
            <button
              onClick={notice.undo}
              className="text-sm font-semibold text-emerald-800 hover:underline cursor-pointer"
            >
              Undo
            </button>
          )}
          <button onClick={onDismiss} aria-label="Dismiss notice" className="text-slate-500 hover:text-slate-800 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

/** Modal used only for irreversible steps: focus lands on Cancel, Escape closes. */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  busy,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4" onClick={onCancel}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-white rounded-xl border border-slate-200 shadow-xl p-5 space-y-4"
      >
        <h2 id="confirm-title" className="text-base font-bold text-slate-900">
          {title}
        </h2>
        <div className="text-sm text-slate-700 space-y-3">{children}</div>
        <div className="flex justify-end gap-2 pt-1">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="px-4 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-sm font-semibold text-slate-700 cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-sm font-semibold cursor-pointer disabled:opacity-50"
          >
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
