"use client";

import React, { useCallback, useMemo, useState } from "react";
import { useAuth, type Role } from "@/context/AuthContext";
import { apiRequest } from "@/lib/api";
import { useAdminData, errText, rolesOf, type AdminUser } from "@/components/admin/AdminData";
import {
  Avatar,
  BTN_PRIMARY,
  BTN_SECONDARY,
  Chip,
  Field,
  INPUT,
  Modal,
  PageHeader,
  Panel,
  ROLES,
  ROLE_LABEL,
  RoleChip,
  RolePicker,
  SearchBox,
  NameFields,
  EMPTY_NAME,
  type NameValue,
  type UserTitle,
  Segmented,
  StatRow,
  TH,
  TableState,
  useToast,
} from "@/components/admin/ui";
import { UserPlus, Users, GraduationCap, UserCheck, UserX, Loader2, Pencil, Wand2 } from "lucide-react";

type RoleFilter = "all" | Role;

function generatePassword(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  const bytes = crypto.getRandomValues(new Uint32Array(12));
  return Array.from(bytes, (b) => chars[b % chars.length]).join("");
}

export default function UsersPage() {
  const { user: me } = useAuth();
  const { users, loaded, error, reload, modulesByOwner, modulesByModerator } = useAdminData();
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return users.filter(
      (u) =>
        (roleFilter === "all" || rolesOf(u).includes(roleFilter)) &&
        (!q || `${u.displayName} ${u.email} ${u.institution || ""}`.toLowerCase().includes(q))
    );
  }, [users, query, roleFilter]);

  // A user with several roles counts once under each of them.
  const count = (r: Role) => users.filter((u) => rolesOf(u).includes(r)).length;
  const disabledCount = users.filter((u) => u.disabled).length;

  return (
    <>
      <PageHeader
        title="Users"
        description="Create sign-in accounts, set roles and institutions, reset passwords, and disable access."
        action={
          <button type="button" className={BTN_PRIMARY} onClick={() => setCreating(true)}>
            <UserPlus className="w-4 h-4" /> New user
          </button>
        }
      />

      <StatRow
        loaded={loaded}
        stats={[
          { label: "All users", value: users.length, icon: Users },
          { label: "Lecturers", value: count("lecturer"), icon: GraduationCap },
          { label: "Moderators", value: count("moderator"), icon: UserCheck },
          { label: "Disabled", value: disabledCount, icon: UserX, warn: disabledCount > 0 },
        ]}
      />

      <Panel>
        <div className="p-3 border-b border-slate-100 flex flex-col lg:flex-row gap-3 lg:items-center">
          <SearchBox value={query} onChange={setQuery} placeholder="Search name, email or institution" />
          <Segmented<RoleFilter>
            label="Filter by role"
            value={roleFilter}
            onChange={setRoleFilter}
            options={[
              { value: "all", label: "All", count: users.length },
              ...ROLES.map((r) => ({ value: r, label: ROLE_LABEL[r], count: count(r) })),
            ]}
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-100">
              <tr>
                <th className={TH}>User</th>
                <th className={TH}>Roles</th>
                <th className={`${TH} hidden md:table-cell`}>Institution</th>
                <th className={`${TH} hidden lg:table-cell`}>Modules</th>
                <th className={TH}>Status</th>
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
                empty={visible.length === 0 ? (users.length ? "No users match these filters." : "No users yet.") : null}
              />
              {loaded &&
                !error &&
                visible.map((u) => {
                  return (
                    <tr key={u.uid} className={`hover:bg-slate-50/70 ${u.disabled ? "text-slate-400" : ""}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <Avatar name={u.displayName} />
                          <div className="min-w-0">
                            <div className="font-semibold text-slate-900 truncate">
                              {u.displayName}
                              {u.email === me.email && <span className="ml-1.5 text-[11px] font-medium text-slate-500">(you)</span>}
                            </div>
                            <div className="text-slate-500 truncate">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {rolesOf(u).map((r) => (
                            <RoleChip key={r} role={r} />
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell text-slate-600">{u.institution || "—"}</td>
                      <td className="px-4 py-3 hidden lg:table-cell text-slate-600">
                        {rolesOf(u).includes("lecturer") || rolesOf(u).includes("moderator") ? (
                          <div className="space-y-0.5">
                            {rolesOf(u).includes("lecturer") && (
                              <div>
                                Lectures <span className="font-mono">{modulesByOwner[u.uid] || 0}</span>
                              </div>
                            )}
                            {rolesOf(u).includes("moderator") && (
                              <div>
                                Moderates <span className="font-mono">{modulesByModerator[u.uid] || 0}</span>
                              </div>
                            )}
                          </div>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {u.disabled ? (
                          <Chip tone="neutral">Disabled</Chip>
                        ) : !u.authProvisioned ? (
                          <Chip tone="caution">Local only</Chip>
                        ) : (
                          <Chip tone="verified">Active</Chip>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => setEditing(u)}
                          aria-label={`Edit ${u.email}`}
                          className={`${BTN_SECONDARY} !px-2.5 !py-1.5`}
                        >
                          <Pencil className="w-3.5 h-3.5" /> Edit
                        </button>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </Panel>

      <CreateUserModal
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={async (created) => {
          setCreating(false);
          toast(
            created.authProvisioned ? "ok" : "error",
            created.authProvisioned
              ? `Created ${created.email}. Share the initial password with them securely.`
              : `Saved ${created.email} locally only: Firebase Admin is not configured, so this account cannot sign in.`
          );
          await reload();
        }}
      />

      {editing && (
        <EditUserModal
          key={editing.uid}
          target={editing}
          isSelf={editing.email === me.email}
          onClose={() => setEditing(null)}
          onSaved={async (msg) => {
            setEditing(null);
            toast("ok", msg);
            await reload();
          }}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------

const EMPTY_CREATE = {
  name: EMPTY_NAME,
  email: "",
  roles: ["lecturer"] as Role[],
  institution: "",
  password: "",
};

function CreateUserModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (u: AdminUser) => Promise<void>;
}) {
  const [form, setForm] = useState(EMPTY_CREATE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = useCallback(() => {
    setForm(EMPTY_CREATE);
    setError(null);
    onClose();
  }, [onClose]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await apiRequest<AdminUser>("/admin/users", {
        method: "POST",
        body: JSON.stringify({
          title: form.name.title || undefined,
          firstName: form.name.firstName.trim(),
          middleName: form.name.middleName.trim(),
          lastName: form.name.lastName.trim(),
          email: form.email.trim(),
          roles: form.roles,
          institution: form.institution.trim() || undefined,
          password: form.password,
        }),
      });
      setForm(EMPTY_CREATE);
      await onCreated(created);
    } catch (err) {
      setError(errText(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="New user"
      description="Creates a Firebase sign-in account with the chosen roles."
      onClose={close}
      footer={
        <>
          <button type="button" className={BTN_SECONDARY} onClick={close}>
            Cancel
          </button>
          <button type="submit" form="create-user-form" className={BTN_PRIMARY} disabled={saving || form.roles.length === 0}>
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {saving ? "Creating…" : "Create account"}
          </button>
        </>
      }
    >
      <form id="create-user-form" onSubmit={submit} className="space-y-4">
        {error && <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>}
        <NameFields value={form.name} onChange={(name) => setForm({ ...form, name })} />
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Email">
            <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="jane@university.edu" className={INPUT} />
          </Field>
          <Field label="Institution">
            <input value={form.institution} onChange={(e) => setForm({ ...form, institution: e.target.value })} placeholder="AssessCraft University" className={INPUT} />
          </Field>
        </div>
        <Field label="Roles" hint="Pick one or more. A lecturer can also moderate other lecturers' modules.">
          <RolePicker value={form.roles} onChange={(roles) => setForm({ ...form, roles })} />
        </Field>
        {(form.roles.includes("lecturer") || form.roles.includes("moderator")) && (
          <p className="text-[11px] text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
            Modules and moderators are paired per module. After creating the account, assign{" "}
            {form.roles.includes("lecturer") && form.roles.includes("moderator")
              ? "the modules this person owns and the ones they moderate"
              : form.roles.includes("lecturer")
              ? "the modules this lecturer writes papers for"
              : "the modules this person moderates"}{" "}
            on the Modules or Assignments page.
          </p>
        )}
        <Field label="Initial password" hint="At least 6 characters. Share it with the user securely.">
          <div className="flex gap-2">
            <input
              required
              minLength={6}
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className={`${INPUT} font-mono`}
            />
            <button type="button" className={BTN_SECONDARY} onClick={() => setForm({ ...form, password: generatePassword() })}>
              <Wand2 className="w-3.5 h-3.5" /> Generate
            </button>
          </div>
        </Field>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------

function EditUserModal({
  target,
  isSelf,
  onClose,
  onSaved,
}: {
  target: AdminUser;
  isSelf: boolean;
  onClose: () => void;
  onSaved: (message: string) => Promise<void>;
}) {
  const [form, setForm] = useState({
    name: {
      title: (target.title ?? "") as UserTitle | "",
      firstName: target.firstName ?? "",
      middleName: target.middleName ?? "",
      lastName: target.lastName ?? "",
    } as NameValue,
    institution: target.institution || "",
    roles: rolesOf(target),
    disabled: target.disabled,
    password: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changes: Record<string, unknown> = {};
  if (form.name.title !== (target.title ?? "")) changes.title = form.name.title;
  for (const part of ["firstName", "middleName", "lastName"] as const) {
    if (form.name[part].trim() !== (target[part] ?? "")) changes[part] = form.name[part].trim();
  }
  if (form.institution.trim() !== (target.institution || "")) changes.institution = form.institution.trim();
  if (form.roles.join() !== rolesOf(target).join()) changes.roles = form.roles;
  const losing = (r: Role) => rolesOf(target).includes(r) && !form.roles.includes(r);
  if (form.disabled !== target.disabled) changes.disabled = form.disabled;
  if (form.password) changes.password = form.password;
  const dirty = Object.keys(changes).length > 0;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dirty) return onClose();
    setSaving(true);
    setError(null);
    try {
      await apiRequest<AdminUser>(`/admin/users/${target.uid}`, { method: "PATCH", body: JSON.stringify(changes) });
      await onSaved(form.password ? `Updated ${target.email} and set a new password.` : `Updated ${target.email}.`);
    } catch (err) {
      setError(errText(err));
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      title={`Edit ${target.displayName}`}
      description={target.email}
      onClose={onClose}
      footer={
        <>
          <button type="button" className={BTN_SECONDARY} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="edit-user-form" className={BTN_PRIMARY} disabled={saving || !dirty || form.roles.length === 0}>
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {saving ? "Saving…" : "Save changes"}
          </button>
        </>
      }
    >
      <form id="edit-user-form" onSubmit={submit} className="space-y-4">
        {error && <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>}
        <NameFields value={form.name} onChange={(name) => setForm({ ...form, name })} />
        <Field label="Institution">
          <input value={form.institution} onChange={(e) => setForm({ ...form, institution: e.target.value })} className={INPUT} />
        </Field>
        <Field
          label="Roles"
          hint={
            form.roles.length === 0
              ? "Pick at least one role."
              : losing("moderator")
              ? "Modules this person moderates will need a new moderator."
              : losing("lecturer")
              ? "Modules this person lectures will show as having no lecturer."
              : isSelf
              ? "You cannot remove your own administrator role."
              : undefined
          }
        >
          <RolePicker value={form.roles} onChange={(roles) => setForm({ ...form, roles })} locked={isSelf ? ["admin"] : []} />
        </Field>

        <div className="rounded-lg border border-slate-200 p-3 flex items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold text-slate-900">Sign-in access</div>
            <div className="text-[11px] text-slate-500">
              {isSelf ? "You cannot disable your own account." : "Disabling signs the user out everywhere."}
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={!form.disabled}
            aria-label="Sign-in access"
            disabled={isSelf}
            onClick={() => setForm({ ...form, disabled: !form.disabled })}
            className={`relative w-10 h-6 rounded-full border transition-colors disabled:opacity-50 ${
              form.disabled ? "bg-slate-200 border-slate-300" : "bg-emerald-700 border-emerald-700"
            }`}
          >
            <span className={`absolute top-0.5 w-4.5 h-4.5 rounded-full bg-white shadow-xs transition-all ${form.disabled ? "left-0.5" : "left-[18px]"}`} />
          </button>
        </div>

        {target.authProvisioned ? (
          <Field label="New password" hint="Leave empty to keep the current password.">
            <div className="flex gap-2">
              <input
                minLength={6}
                autoComplete="new-password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Unchanged"
                className={`${INPUT} font-mono`}
              />
              <button type="button" className={BTN_SECONDARY} onClick={() => setForm({ ...form, password: generatePassword() })}>
                <Wand2 className="w-3.5 h-3.5" /> Generate
              </button>
            </div>
          </Field>
        ) : (
          <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            This is a local record without a sign-in account, so it has no password.
          </p>
        )}
      </form>
    </Modal>
  );
}
