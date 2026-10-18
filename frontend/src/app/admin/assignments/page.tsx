"use client";

import React, { useState } from "react";
import { apiRequest } from "@/lib/api";
import { useAdminData, errText, rolesOf, type AdminUser, type Module } from "@/components/admin/AdminData";
import { Avatar, Chip, PageHeader, Panel, SearchBox, Segmented, StatRow, TH, TableState, useToast } from "@/components/admin/ui";
import { Library, UserX, ShieldQuestion, CheckCircle2, Loader2 } from "lucide-react";

type View = "modules" | "lecturers";
type Scope = "all" | "open";

const SELECT =
  "w-full min-w-[160px] max-w-[240px] text-xs rounded-lg border px-2.5 py-1.5 bg-white focus:outline-none focus:border-emerald-700 focus:ring-1 focus:ring-emerald-700 disabled:opacity-60";

function PersonSelect({
  label,
  value,
  people,
  emptyLabel,
  noneLabel,
  busy,
  onChange,
  unavailable = {},
}: {
  label: string;
  value: string;
  people: AdminUser[];
  emptyLabel: string;
  noneLabel: string;
  busy: boolean;
  onChange: (uid: string) => void;
  /** People listed but not selectable, with the reason shown next to their name. */
  unavailable?: Record<string, string>;
}) {
  return (
    <div className="flex items-center gap-2">
      <select
        aria-label={label}
        value={value}
        disabled={busy || people.length === 0}
        onChange={(e) => onChange(e.target.value)}
        className={`${SELECT} ${value ? "border-slate-200" : "border-amber-300 bg-amber-50 text-amber-900"}`}
      >
        <option value="">{people.length ? emptyLabel : noneLabel}</option>
        {people.map((p) => (
          <option key={p.uid} value={p.uid} disabled={Boolean(unavailable[p.uid])}>
            {p.displayName}
            {unavailable[p.uid] ? ` (${unavailable[p.uid]})` : ""}
          </option>
        ))}
      </select>
      {busy && <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-500" />}
    </div>
  );
}

export default function AssignmentsPage() {
  const { modules, lecturers, moderators, moderatorCandidates, byUid, ownerOf, moderatorOf, modulesByModerator, loaded, error, reload } =
    useAdminData();
  const toast = useToast();
  const [view, setView] = useState<View>("modules");
  const [scope, setScope] = useState<Scope>("all");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const complete = (m: Module) => Boolean(ownerOf(m) && moderatorOf(m));
  const noOwner = modules.filter((m) => !ownerOf(m)).length;
  const noModerator = modules.filter((m) => !moderatorOf(m)).length;
  const ready = modules.filter(complete).length;
  const maxLoad = Math.max(1, ...moderators.map((m) => modulesByModerator[m.uid] || 0));

  const q = query.trim().toLowerCase();
  const matches = (m: Module) =>
    !q || `${m.code} ${m.title} ${ownerOf(m)?.displayName || ""} ${moderatorOf(m)?.displayName || ""}`.toLowerCase().includes(q);
  const visibleModules = modules.filter((m) => (scope === "all" || !complete(m)) && matches(m));

  const lecturerGroups = lecturers
    .map((l) => ({ lecturer: l, modules: modules.filter((m) => ownerOf(m)?.uid === l.uid) }))
    .filter(
      (g) =>
        (scope === "all" || g.modules.some((m) => !moderatorOf(m))) &&
        (!q || `${g.lecturer.displayName} ${g.lecturer.email}`.toLowerCase().includes(q) || g.modules.some(matches))
    );

  const assign = async (m: Module, field: "ownerUid" | "moderatorUid", uid: string) => {
    const key = `${m.id}:${field}`;
    const person = uid ? byUid[uid] : undefined;
    setBusy(key);
    try {
      await apiRequest(`/courses/${m.id}`, { method: "PATCH", body: JSON.stringify({ [field]: uid }) });
      toast(
        "ok",
        field === "ownerUid"
          ? person
            ? `${person.displayName} is now the lecturer for ${m.code}.`
            : `${m.code} no longer has a lecturer.`
          : person
          ? `${person.displayName} now moderates ${m.code}.${
              rolesOf(person).includes("moderator") ? "" : " The Moderator role was added to their account."
            }`
          : `${m.code} no longer has a moderator.`
      );
      await reload();
    } catch (err) {
      toast("error", errText(err));
    } finally {
      setBusy(null);
    }
  };

  const moderatorSelect = (m: Module) => (
    <PersonSelect
      label={`Moderator for ${m.code}`}
      value={moderatorOf(m)?.uid || ""}
      people={moderatorCandidates}
      unavailable={ownerOf(m) ? { [ownerOf(m)!.uid]: "lecturer of this module" } : {}}
      emptyLabel="No moderator"
      noneLabel="No moderators yet"
      busy={busy === `${m.id}:moderatorUid`}
      onChange={(uid) => assign(m, "moderatorUid", uid)}
    />
  );

  return (
    <>
      <PageHeader
        title="Assignments"
        description="Moderation is set per module: each module has a lecturer who writes its papers and a moderator. A lecturer with two modules can have a different moderator for each. Both people are notified of every change."
      />

      <StatRow
        loaded={loaded}
        stats={[
          { label: "Modules", value: modules.length, icon: Library },
          { label: "Ready for moderation", value: ready, icon: CheckCircle2 },
          { label: "Without a lecturer", value: noOwner, icon: UserX, warn: noOwner > 0 },
          { label: "Without a moderator", value: noModerator, icon: ShieldQuestion, warn: noModerator > 0 },
        ]}
      />

      <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
        <Segmented<View>
          label="Group by"
          value={view}
          onChange={setView}
          options={[
            { value: "modules", label: "By module" },
            { value: "lecturers", label: "By lecturer" },
          ]}
        />
        <SearchBox value={query} onChange={setQuery} placeholder="Search modules, lecturers or moderators" />
        <Segmented<Scope>
          label="Show"
          value={scope}
          onChange={setScope}
          options={[
            { value: "all", label: "All" },
            { value: "open", label: "Needs assignment", count: modules.length - ready },
          ]}
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2">
          {view === "modules" ? (
            <Panel className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50/80 border-b border-slate-100">
                    <tr>
                      <th className={TH}>Module</th>
                      <th className={TH}>Lecturer</th>
                      <th className={TH}>Moderator</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <TableState
                      loaded={loaded}
                      error={error}
                      colSpan={3}
                      empty={
                        visibleModules.length
                          ? null
                          : modules.length
                          ? scope === "open"
                            ? "Every module has a lecturer and a moderator."
                            : "No modules match."
                          : "No modules yet. Create them on the Modules page."
                      }
                    />
                    {loaded &&
                      !error &&
                      visibleModules.map((m) => (
                        <tr key={m.id} className="hover:bg-slate-50/70">
                          <td className="px-4 py-3">
                            <div className="font-mono text-sm font-bold text-slate-900">{m.code}</div>
                            <div className="text-slate-600">{m.title}</div>
                          </td>
                          <td className="px-4 py-3">
                            <PersonSelect
                              label={`Lecturer for ${m.code}`}
                              value={ownerOf(m)?.uid || ""}
                              people={lecturers}
                              unavailable={moderatorOf(m) ? { [moderatorOf(m)!.uid]: "moderator of this module" } : {}}
                              emptyLabel="No lecturer"
                              noneLabel="No lecturers yet"
                              busy={busy === `${m.id}:ownerUid`}
                              onChange={(uid) => assign(m, "ownerUid", uid)}
                            />
                          </td>
                          <td className="px-4 py-3">{moderatorSelect(m)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ) : !loaded ? (
            <Panel className="p-6 text-xs text-slate-500">Loading…</Panel>
          ) : lecturerGroups.length === 0 ? (
            <Panel className="p-6 text-xs text-slate-500 text-center">
              {lecturers.length
                ? scope === "open"
                  ? "Every lecturer's modules have a moderator."
                  : "No lecturers match."
                : "No active lecturers yet. Create them on the Users page."}
            </Panel>
          ) : (
            <div className="space-y-4">
              {lecturerGroups.map(({ lecturer, modules: owned }) => {
                const distinct = new Set(owned.map((m) => moderatorOf(m)?.uid).filter(Boolean)).size;
                return (
                  <Panel key={lecturer.uid} className="overflow-hidden">
                    <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-3">
                      <Avatar name={lecturer.displayName} />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-slate-900 truncate">{lecturer.displayName}</div>
                        <div className="text-xs text-slate-500 truncate">{lecturer.email}</div>
                      </div>
                      <div className="text-right text-[11px] text-slate-500">
                        <div>
                          <span className="font-mono text-slate-700">{owned.length}</span> module(s)
                        </div>
                        <div>
                          <span className="font-mono text-slate-700">{distinct}</span> moderator(s)
                        </div>
                      </div>
                    </div>
                    {owned.length === 0 ? (
                      <p className="px-4 py-4 text-xs text-slate-500">
                        Not the lecturer for any module yet. Assign one in the <span className="font-semibold">By module</span> view.
                      </p>
                    ) : (
                      <ul className="divide-y divide-slate-100">
                        {owned.map((m) => (
                          <li key={m.id} className="px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                            <div className="flex-1 min-w-0">
                              <span className="font-mono text-xs font-bold text-slate-900">{m.code}</span>
                              <span className="text-xs text-slate-600"> · {m.title}</span>
                            </div>
                            {moderatorSelect(m)}
                          </li>
                        ))}
                      </ul>
                    )}
                  </Panel>
                );
              })}
            </div>
          )}
        </div>

        <Panel className="p-5 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Moderator load</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">Modules each active moderator reviews.</p>
          </div>
          {!loaded ? (
            <p className="text-xs text-slate-500">Loading…</p>
          ) : moderators.length === 0 ? (
            <p className="text-xs text-slate-500">No active moderators yet. Create one on the Users page.</p>
          ) : (
            <ul className="space-y-3">
              {moderators.map((mod) => {
                const n = modulesByModerator[mod.uid] || 0;
                const codes = modules.filter((m) => moderatorOf(m)?.uid === mod.uid).map((m) => m.code);
                return (
                  <li key={mod.uid}>
                    <div className="flex items-center justify-between text-xs gap-2">
                      <span className="font-medium text-slate-800 truncate">{mod.displayName}</span>
                      <span className="font-mono text-slate-600">{n}</span>
                    </div>
                    <div className="mt-1.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full rounded-full bg-slate-400" style={{ width: `${(n / maxLoad) * 100}%` }} />
                    </div>
                    {codes.length > 0 && <div className="mt-1 font-mono text-[11px] text-slate-500 truncate">{codes.join(", ")}</div>}
                  </li>
                );
              })}
            </ul>
          )}
          {noModerator > 0 && loaded && (
            <div className="pt-1">
              <Chip tone="caution">
                <span className="font-mono">{noModerator}</span>&nbsp;module(s) cannot be submitted yet
              </Chip>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
