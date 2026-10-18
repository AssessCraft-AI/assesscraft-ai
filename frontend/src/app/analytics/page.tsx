"use client";

import React, { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api";
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  Database,
  Shield,
  Layers,
} from "lucide-react";

interface FlagCount {
  type: string;
  count: number;
}

interface StageTiming {
  stage: string;
  avgMinutes: number;
}

interface TelemetryEvent {
  event_id: string;
  ts: string;
  user_role: string;
  assessment_id?: string;
  stage?: string;
  event_type: string;
  flag_type?: string;
  resolution?: string;
  duration_ms?: number;
  meta?: Record<string, any>;
}

interface AnalyticsData {
  totalAssessments: number;
  papersGenerated: number;
  assessCraftMinutesPerPaper: number;
  acceptanceRatePercent: number;
  flagsRaisedByType: FlagCount[];
  timePerStage: StageTiming[];
  totalLoggedEvents: number;
  flagsDecided?: number;
  recentEvents?: TelemetryEvent[];
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchAnalytics() {
      try {
        setLoading(true);
        const res = await apiRequest<AnalyticsData>("/analytics/summary");
        setData(res);
      } catch (err: any) {
        console.error("Failed to load analytics:", err);
        setError(err.message || "Could not load analytics");
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, []);

  const papersCount = data?.papersGenerated ?? 0;
  const hasTiming = (data?.timePerStage?.length ?? 0) > 0;
  const fmtMinutes = (m: number) => (m >= 1 ? `${Math.round(m * 10) / 10} min` : m * 60 >= 1 ? `${Math.round(m * 60)} s` : "under 1 s");
  const decidedFlags = data?.flagsDecided ?? 0;

  const totalFlagsDetected = data?.flagsRaisedByType?.reduce((acc, curr) => acc + curr.count, 0) ?? 0;

  if (error || (loading && !data)) {
    return (
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-4">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Analytics</h1>
        {error ? (
          <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 flex flex-wrap items-center gap-3">
            <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden />
            <span className="flex-1">Couldn&apos;t load analytics ({error}). Check that the backend is running, then retry.</span>
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1.5 rounded-lg bg-white border border-rose-200 text-rose-800 font-semibold hover:bg-rose-100 cursor-pointer"
            >
              Retry
            </button>
          </div>
        ) : (
          <p className="text-sm text-slate-500" role="status">Loading analytics…</p>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Analytics
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Measured from this workspace: agent run times, reviewer flags, and how lecturers decided them.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-white border border-slate-200 p-2.5 rounded-lg shadow-xs">
          <span className="text-xs text-slate-700">
            Events logged: <strong className="font-mono text-slate-900">{data?.totalLoggedEvents || 0}</strong>
          </span>
        </div>
      </div>

      {/* Measured metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* KPI 1: Measured agent run time */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3 hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Agent run time</span>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center font-bold">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {hasTiming ? fmtMinutes(data?.assessCraftMinutesPerPaper ?? 0) : "—"}
            </div>
            <div className="text-xs text-slate-600 mt-1">
              {hasTiming ? "Average per assessment, all agents" : "No timed runs yet"}
            </div>
          </div>
          <div className="text-xs text-slate-500 pt-1 border-t border-slate-100">
            Excludes lecturer review time
          </div>
        </div>

        {/* KPI 2: Share of decided flags the lecturer upheld */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3 hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Flags upheld</span>
            <div className="w-9 h-9 rounded-lg bg-sky-50 border border-sky-200 text-sky-600 flex items-center justify-center font-bold">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {decidedFlags > 0 ? `${data?.acceptanceRatePercent}%` : "—"}
            </div>
            <div className="text-xs text-slate-600 mt-1">
              {decidedFlags > 0
                ? `Of ${decidedFlags} decided reviewer flags, the lecturer agreed with`
                : "No reviewer flags decided yet"}
            </div>
          </div>
          {decidedFlags > 0 && (
            <div className="text-xs text-slate-500 pt-1 border-t border-slate-100">
              The rest were kept after review
            </div>
          )}
        </div>

        {/* KPI 3: Reviewer flags raised */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3 hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Flags raised</span>
            <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 flex items-center justify-center font-bold">
              <Shield className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {totalFlagsDetected}
            </div>
            <div className="text-xs text-slate-600 mt-1">
              Possible problems for a lecturer to decide
            </div>
          </div>
          <div className="text-xs text-slate-500 pt-1 border-t border-slate-100">
            Reviewer blind-solve and duplicate checks
          </div>
        </div>

        {/* KPI 4: Parallel Papers Generated */}
        <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3 hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Parallel versions</span>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center font-bold">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
              {papersCount}
            </div>
            <div className="text-xs text-slate-600 mt-1">
              Main and repeat papers assembled
            </div>
          </div>
          <div className="text-xs text-slate-500 pt-1 border-t border-slate-100">
            Assembled with OR-Tools CP-SAT
          </div>
        </div>
      </div>

      {/* 2-Column Visual Charts Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Stage-by-Stage Workflow Duration Breakdown */}
        <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-emerald-600" />
                <span>Agent time per stage</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Average measured run time of each agent
              </p>
            </div>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
              {fmtMinutes(data?.assessCraftMinutesPerPaper ?? 0)} total
            </span>
          </div>

          <div className="space-y-3 pt-2">
            {data?.timePerStage?.map((stage, idx) => {
              const maxMins = 5.0;
              const pct = Math.min(100, (stage.avgMinutes / maxMins) * 100);
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-700 font-medium">{stage.stage}</span>
                    <span className="text-slate-500 font-mono font-bold">
                      {fmtMinutes(stage.avgMinutes)}
                    </span>
                  </div>
                  <div className="w-full h-2.5 rounded-full bg-slate-100 border border-slate-200 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-emerald-700 transition-all duration-700"
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>

          {!data?.timePerStage?.length && (
            <p className="text-xs text-slate-500">No timed agent runs yet.</p>
          )}
        </div>

        {/* Chart 2: Flags Detected by Adversarial Reviewer */}
        <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Shield className="w-4 h-4 text-amber-600" />
                <span>Reviewer flags by type</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every flag raised, whatever the lecturer later decided
              </p>
            </div>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
              {totalFlagsDetected} total
            </span>
          </div>

          <div className="space-y-3 pt-2">
            {data?.flagsRaisedByType?.map((flag, idx) => {
              const maxCount = 8;
              const pct = Math.min(100, (flag.count / maxCount) * 100);
              const isHighSeverity = flag.type.includes("Mismatch") || flag.type.includes("Past");
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-700 font-medium flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${isHighSeverity ? "bg-rose-500" : "bg-amber-500"}`}></span>
                      <span>{flag.type}</span>
                    </span>
                    <span className="text-slate-500 font-mono font-bold">
                      {flag.count} flagged
                    </span>
                  </div>
                  <div className="w-full h-2.5 rounded-full bg-slate-100 border border-slate-200 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        isHighSeverity
                          ? "bg-rose-500"
                          : "bg-amber-500"
                      }`}
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recent telemetry events */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Database className="w-5 h-5 text-emerald-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Recent events
              </h3>
              <p className="text-xs text-slate-500">
                Stage runs, flag decisions, and exports. Also sent to BigQuery when it&apos;s configured.
              </p>
            </div>
          </div>
          <span className="text-xs font-mono text-slate-500">
            Last {data?.recentEvents?.length || 0}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-mono border-b border-slate-200 uppercase text-[11px] tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Time</th>
                <th className="py-3 px-4">Event</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Assessment</th>
                <th className="py-3 px-4">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
              {data?.recentEvents && data.recentEvents.length > 0 ? (
                data.recentEvents.map((ev, i) => (
                  <tr key={ev.event_id || i} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {new Date(ev.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 font-semibold text-emerald-700 whitespace-nowrap">
                      {ev.event_type}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] bg-slate-100 border border-slate-200 text-slate-700 font-semibold">
                        {ev.user_role}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {ev.assessment_id || "—"}
                    </td>
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {ev.duration_ms ? `${ev.duration_ms} ms` : "—"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No events yet. Running an agent, deciding a flag, or exporting a file records one here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
