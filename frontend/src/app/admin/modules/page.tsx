"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";
import { useAdminData, errText, type AdminUser, type Module } from "@/components/admin/AdminData";
import {
  BTN_DANGER,
  BTN_PRIMARY,
  BTN_SECONDARY,
  Chip,
  Field,
  INPUT,
  Modal,
  PageHeader,
  Panel,
  SearchBox,
  Segmented,
  StatRow,
  TH,
  TableState,
  useToast,
} from "@/components/admin/ui";
import { Plus, Library, UserX, ShieldQuestion, CheckCircle2, Loader2, Pencil, Trash2, ArrowUpRight } from "lucide-react";

type ModuleFilter = "all" | "no_owner" | "no_moderator" | "draft";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export default function ModulesPage() {
  const { modules, loaded, error, reload, lecturers, moderatorCandidates, ownerOf, moderatorOf } = useAdminData();
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ModuleFilter>("all");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Module | null>(null);
  const [deleting, setDeleting] = useState<Module | null>(null);

  const noOwner = modules.filter((m) => !ownerOf(m)).length;
  const noModerator = modules.filter((m) => !moderatorOf(m)).length;
  const confirmed = modules.filter((m) => m.confirmed).length;

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return modules.filter((m) => {
      if (filter === "no_owner" && ownerOf(m)) return false;
      if (filter === "no_moderator" && moderatorOf(m)) return false;
      if (filter === "draft" && m.confirmed) return false;
      const people = `${ownerOf(m)?.displayName || ""} ${moderatorOf(m)?.displayName || ""}`;
      return !q || `${m.code} ${m.title} ${people}`.toLowerCase().includes(q);
    });
  }, [modules, query, filter, ownerOf, moderatorOf]);

  return (
    <>
      <PageHeader
        title="Modules"
        description="Create modules and choose, for each one, the lecturer who writes its papers and the moderator who reviews them. Lecturers set the learning outcomes."
        action={
          <button type="button" className={BTN_PRIMARY} onClick={() => setCreating(true)}>
            <Plus className="w-4 h-4" /> New module
          </button>
        }
      />

      <StatRow
        loaded={loaded}
        stats={[
          { label: "Modules", value: modules.length, icon: Library },
          { label: "Without a lecturer", value: noOwner, icon: UserX, warn: noOwner > 0 },
          { label: "Without a moderator", value: noModerator, icon: ShieldQuestion, warn: noModerator > 0 },
          { label: "Outcomes confirmed", value: confirmed, icon: CheckCircle2 },
        ]}
      />

      <Panel>
        <div className="p-3 border-b border-slate-100 flex flex-col lg:flex-row gap-3 lg:items-center">
          <SearchBox value={query} onChange={setQuery} placeholder="Search code, title, lecturer or moderator" />
          <Segmented<ModuleFilter>
            label="Filter modules"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "all", label: "All", count: modules.length },
              { value: "no_owner", label: "No lecturer", count: noOwner },
              { value: "no_moderator", label: "No moderator", count: noModerator },
              { value: "draft", label: "Outcomes in draft", count: modules.length - confirmed },
            ]}
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-100">
              <tr>
                <th className={TH}>Module</th>
                <th className={TH}>Lecturer</th>
                <th className={TH}>Moderator</th>
                <th className={`${TH} hidden md:table-cell`}>Outcomes</th>
                <th className={`${TH} hidden lg:table-cell`}>Updated</th>
                <th className={`${TH} text-right`}>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <TableState
                loaded={loaded}
                error={error}
                colSpan={6}
                empty={visible.length === 0 ? (modules.length ? "No modules match these filters." : "No modules yet. Create the first one.") : null}
              />
              {loaded &&
                !error &&
                visible.map((m) => {
                  const owner = ownerOf(m);
                  const mod = moderatorOf(m);
                  return (
                    <tr key={m.id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3">
                        <Link href={`/courses/${m.code}`} className="group inline-flex items-center gap-1 font-mono text-sm font-bold text-slate-900 hover:text-emerald-800">
                          {m.code}
                          <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-700" />
                        </Link>
                        <div className="text-slate-600">{m.title}</div>
                      </td>
                      <td className="px-4 py-3">
                        {owner ? (
                          <>
                            <div className="font-medium text-slate-900">{owner.displayName}</div>
                            <div className="text-slate-500">{owner.email}</div>
                          </>
                        ) : (
                          <Chip tone="caution">No lecturer</Chip>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {mod ? (
                          <>
                            <div className="font-medium text-slate-900">{mod.displayName}</div>
                            <div className="text-slate-500">{mod.email}</div>
                          </>
                        ) : (
                          <Chip tone="caution">No moderator</Chip>
                        )}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <div className="flex items-center gap-2">
                          {m.confirmed ? <Chip tone="verified">Confirmed</Chip> : <Chip tone="neutral">Draft</Chip>}
                          <span className="text-slate-500">
                            <span className="font-mono">{m.clos?.length ?? 0}</span> CLOs ·{" "}
                            <span className="font-mono">{m.topics?.length ?? 0}</span> topics
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell font-mono text-slate-500">{formatDate(m.updatedAt)}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1.5">
                          <button type="button" onClick={() => setEditing(m)} aria-label={`Edit ${m.code}`} className={`${BTN_SECONDARY} !px-2.5 !py-1.5`}>
                            <Pencil className="w-3.5 h-3.5" /> Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => setDeleting(m)}
                            aria-label={`Delete ${m.code}`}
                            title="Delete module"
                            className={`${BTN_SECONDARY} !px-2 !py-1.5 hover:!border-rose-200 hover:!bg-rose-50 hover:!text-rose-700`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </Panel>

      {creating && (
        <ModuleFormModal
          lecturers={lecturers}
          moderators={moderatorCandidates}
          onClose={() => setCreating(false)}
          onSaved={async (m) => {
            setCreating(false);
            toast("ok", `Created module ${m.code} · ${m.title}.`);
            await reload();
          }}
        />
      )}

      {editing && (
        <ModuleFormModal
          key={editing.id}
          module={editing}
          currentOwner={ownerOf(editing)}
          currentModerator={moderatorOf(editing)}
          lecturers={lecturers}
          moderators={moderatorCandidates}
          onClose={() => setEditing(null)}
          onSaved={async (m) => {
            setEditing(null);
            toast("ok", `Updated ${m.code}.`);
            await reload();
          }}
        />
      )}

      {deleting && (
        <DeleteModuleModal
          module={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={async () => {
            toast("ok", `Deleted module ${deleting.code}.`);
            setDeleting(null);
            await reload();
          }}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------

function ModuleFormModal({
  module,
  currentOwner,
  currentModerator,
  lecturers,
  moderators,
  onClose,
  onSaved,
}: {
  module?: Module;
  currentOwner?: AdminUser;
  currentModerator?: AdminUser;
  lecturers: AdminUser[];
  moderators: AdminUser[];
  onClose: () => void;
  onSaved: (m: Module) => Promise<void>;
}) {
  const editing = Boolean(module);
  const [form, setForm] = useState({
    code: module?.code || "",
    title: module?.title || "",
    ownerUid: currentOwner?.uid || "",
    moderatorUid: currentModerator?.uid || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const saved = module
        ? await apiRequest<Module>(`/courses/${module.id}`, {
            method: "PATCH",
            body: JSON.stringify({ title: form.title.trim(), ownerUid: form.ownerUid, moderatorUid: form.moderatorUid }),
          })
        : await apiRequest<Module>("/courses", {
            method: "POST",
            body: JSON.stringify({
              code: form.code.trim().toUpperCase(),
              title: form.title.trim(),
              ownerUid: form.ownerUid || undefined,
              moderatorUid: form.moderatorUid || undefined,
            }),
          });
      await onSaved(saved);
    } catch (err) {
      setError(errText(err));
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      title={editing ? `Edit ${module!.code}` : "New module"}
      description={editing ? "The module code is permanent; the title, lecturer and moderator can change." : "Lecturers can add outcomes and materials once the module exists."}
      onClose={onClose}
      footer={
        <>
          <button type="button" className={BTN_SECONDARY} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="module-form" className={BTN_PRIMARY} disabled={saving}>
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {saving ? "Saving…" : editing ? "Save changes" : "Create module"}
          </button>
        </>
      }
    >
      <form id="module-form" onSubmit={submit} className="space-y-4">
        {error && <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>}
        <div className="grid sm:grid-cols-3 gap-4">
          <Field label="Code">
            <input
              required
              disabled={editing}
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
              placeholder="IT3020"
              className={`${INPUT} font-mono uppercase`}
            />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Title">
              <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Database Systems" className={INPUT} />
            </Field>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Lecturer" hint={lecturers.length ? "Writes this module's papers." : "No active lecturers yet. Create one on the Users page."}>
            <select value={form.ownerUid} onChange={(e) => setForm({ ...form, ownerUid: e.target.value })} className={INPUT}>
              <option value="">No lecturer yet</option>
              {lecturers.map((l) => (
                <option key={l.uid} value={l.uid} disabled={l.uid === form.moderatorUid}>
                  {l.displayName} ({l.uid === form.moderatorUid ? "moderator of this module" : l.email})
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Moderator"
            hint={
              moderators.length
                ? "Reviews papers submitted for this module. Picking a lecturer adds the Moderator role to their account."
                : "No active moderators or lecturers yet. Create one on the Users page."
            }
          >
            <select value={form.moderatorUid} onChange={(e) => setForm({ ...form, moderatorUid: e.target.value })} className={INPUT}>
              <option value="">No moderator yet</option>
              {moderators.map((m) => (
                <option key={m.uid} value={m.uid} disabled={m.uid === form.ownerUid}>
                  {m.displayName} ({m.uid === form.ownerUid ? "lecturer of this module" : m.email})
                </option>
              ))}
            </select>
          </Field>
        </div>
        {editing && form.moderatorUid !== (currentModerator?.uid || "") && (
          <p className="text-[11px] text-sky-800 bg-sky-50 border border-sky-200 rounded-lg px-3 py-2">
            Papers already in moderation stay with the moderator they were sent to; new submissions go to the new moderator.
          </p>
        )}
      </form>
    </Modal>
  );
}

function DeleteModuleModal({ module, onClose, onDeleted }: { module: Module; onClose: () => void; onDeleted: () => Promise<void> }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmDelete = async () => {
    setSaving(true);
    setError(null);
    try {
      await apiRequest(`/courses/${module.id}`, { method: "DELETE" });
      await onDeleted();
    } catch (err) {
      setError(errText(err));
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      title={`Delete ${module.code}?`}
      description="This cannot be undone."
      onClose={onClose}
      footer={
        <>
          <button type="button" data-autofocus className={BTN_SECONDARY} onClick={onClose}>
            Cancel
          </button>
          <button type="button" className={BTN_DANGER} disabled={saving} onClick={confirmDelete}>
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {saving ? "Deleting…" : "Delete module"}
          </button>
        </>
      }
    >
      {error && <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>}
      <p className="text-xs text-slate-700">
        <span className="font-mono font-semibold">{module.code}</span> · {module.title} and its learning outcomes will be removed. A module
        that still has assessments cannot be deleted.
      </p>
    </Modal>
  );
}
