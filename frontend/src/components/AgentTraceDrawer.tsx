"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { apiRequest } from "@/lib/api";
import { FileText, Loader2, RefreshCw, X, Zap } from "lucide-react";

export interface RunStep {
  stepId: string;
  agent: string;
  tool?: string;
  input_summary: string;
  output_summary: string;
  sources: string[];
  startedAt: string;
  endedAt?: string;
  status: "running" | "completed" | "failed";
  durationMs?: number;
}

export interface RunTrace {
  id: string;
  assessmentId?: string;
  courseId?: string;
  workflow: string;
  status: "running" | "completed" | "failed";
  steps: RunStep[];
  createdAt: string;
  updatedAt: string;
}

interface AgentTraceDrawerProps {
  runId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function AgentTraceDrawer({ runId, isOpen, onClose }: AgentTraceDrawerProps) {
  const [trace, setTrace] = useState<RunTrace | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrace = useCallback(async () => {
    if (!runId) return;
    try {
      const data = await apiRequest<RunTrace>(`/runs/${runId}`);
      setTrace(data);
      setError(null);
    } catch (err: any) {
      console.warn("Failed to fetch run trace:", err.message);
      setError("Run trace initializing or unavailable");
    }
  }, [runId]);

  useEffect(() => {
    if (!isOpen || !runId) return;
    setLoading(true);
    fetchTrace().finally(() => setLoading(false));
  }, [isOpen, runId, fetchTrace]);

  // Poll only while the run is in flight; idle polling kept Cloud Run awake and burned Firestore reads.
  // A run whose steps all completed is complete, whatever the stored run status says.
  const status =
    trace && trace.steps.length > 0 && trace.steps.every((st) => st.status === "completed") ? "completed" : trace?.status;
  const finished = status === "completed" || status === "failed";
  useEffect(() => {
    if (!isOpen || !runId || finished) return;
    const interval = setInterval(fetchTrace, 2000);
    return () => clearInterval(interval);
  }, [isOpen, runId, finished, fetchTrace]);

  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!isOpen) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getAgentColor = (agent: string) => {
    switch (agent) {
      case "DocIntel":
      case "Blueprint":
      case "ItemWriter":
        return "text-sky-700 border-sky-200 bg-sky-50";
      case "Reviewer":
      case "Moderation":
        return "text-amber-800 border-amber-200 bg-amber-50";
      default:
        return "text-slate-700 border-slate-200 bg-slate-100";
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 flex justify-end" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="trace-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl h-full bg-white border-l border-slate-200 shadow-2xl flex flex-col"
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-100 bg-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 font-bold">
              <Zap className="w-5 h-5" aria-hidden />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="trace-title" className="text-base font-bold text-slate-900">Agent execution trace</h2>
                {status === "running" && (
                  <span className="flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 animate-pulse font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                    Running
                  </span>
                )}
                {status === "completed" && (
                  <span className="flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    Completed
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                Run ID: {runId || "none"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchTrace}
              title="Refresh Trace"
              aria-label="Refresh trace"
              className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition cursor-pointer"
            >
              <RefreshCw className="w-5 h-5" aria-hidden />
            </button>
            <button
              ref={closeRef}
              onClick={onClose}
              aria-label="Close agent trace"
              className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 bg-slate-50/50">
          {error && (
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs">
              {error}
            </div>
          )}

          {loading && !trace && (
            <div className="flex items-center justify-center py-12 text-slate-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> Loading agent trace...
            </div>
          )}

          {trace && trace.steps.length === 0 && (
            <div className="text-center py-12 text-slate-500 text-sm">
              No trace steps recorded yet. Agent tasks will stream here in real time.
            </div>
          )}

          {trace && trace.steps.length > 0 && (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
              {trace.steps.map((step, idx) => (
                <div key={step.stepId || idx} className="relative group">
                  {/* Step Status Node */}
                  <div
                    className={`absolute -left-6 top-1.5 w-5 h-5 rounded-full border-2 border-white flex items-center justify-center text-[11px] font-bold shadow-xs ${
                      step.status === "completed"
                        ? "bg-emerald-700 text-white"
                        : step.status === "running"
                        ? "bg-sky-500 text-white animate-pulse"
                        : "bg-rose-500 text-white"
                    }`}
                  >
                    {step.status === "completed" ? "✓" : idx + 1}
                  </div>

                  {/* Step Card */}
                  <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-xs hover:border-slate-300 transition">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${getAgentColor(
                            step.agent
                          )}`}
                        >
                          {step.agent}
                        </span>
                        {step.tool && (
                          <span className="text-xs font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                            {step.tool}
                          </span>
                        )}
                      </div>
                      {step.durationMs != null && (
                        <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                          {step.durationMs > 1000
                            ? `${(step.durationMs / 1000).toFixed(2)}s`
                            : `${step.durationMs}ms`}
                        </span>
                      )}
                    </div>

                    {/* Input Summary */}
                    <div className="text-xs text-slate-600 mb-2">
                      <span className="text-slate-800 font-semibold">Input: </span>
                      {step.input_summary}
                    </div>

                    {/* Output Summary */}
                    <div className="text-xs text-slate-800 bg-emerald-50/70 p-2.5 rounded-lg border border-emerald-200/80">
                      <span className="text-emerald-700 font-semibold">Result: </span>
                      {step.output_summary}
                    </div>

                    {/* Sources Cited */}
                    {step.sources && step.sources.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap gap-1.5 items-center">
                        <span className="text-[11px] text-slate-500 font-medium">Citations:</span>
                        {step.sources.map((src, sIdx) => (
                          <span
                            key={sIdx}
                            className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 truncate max-w-[200px]"
                            title={src}
                          >
                            <FileText className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> {src}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-between items-center text-xs text-slate-500">
          <span>Workflow: {trace?.workflow || "assessment_generation"}</span>
          <span>{trace?.steps.length || 0} step(s) recorded</span>
        </div>
      </div>
    </div>
  );
}
