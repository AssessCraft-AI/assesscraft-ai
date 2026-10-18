"use client";

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { Role } from "@/context/AuthContext";
import { CheckCircle2, AlertTriangle, X, Loader2, Search } from "lucide-react";

// ---------------------------------------------------------------------------
// Tokens
// ---------------------------------------------------------------------------

export const INPUT =
  "w-full px-3.5 py-2.5 text-sm rounded-lg bg-white border border-slate-200 text-slate-900 placeholder-slate-400 shadow-xs focus:outline-none focus:border-emerald-700 focus:ring-1 focus:ring-emerald-700 disabled:bg-slate-50 disabled:text-slate-500";

export const BTN_PRIMARY =
  "inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold shadow-xs disabled:opacity-50 disabled:pointer-events-none";

export const BTN_SECONDARY =
  "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 hover:border-slate-300 text-slate-700 text-xs font-semibold shadow-xs disabled:opacity-50 disabled:pointer-events-none";

export const BTN_DANGER =
  "inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-rose-700 hover:bg-rose-800 text-white text-xs font-semibold shadow-xs disabled:opacity-50 disabled:pointer-events-none";

export const ROLE_LABEL: Record<Role, string> = {
  admin: "Administrator",
  lecturer: "Lecturer",
  moderator: "Moderator",
};

const ROLE_STYLE: Record<Role, string> = {
  admin: "bg-slate-100 text-slate-900 border-slate-300",
  lecturer: "bg-sky-50 text-sky-800 border-sky-200",
  moderator: "bg-amber-50 text-amber-800 border-amber-200",
};

export const ROLES = Object.keys(ROLE_LABEL) as Role[];

export const TITLES = ["Dr.", "Prof.", "Mr.", "Mrs.", "Ms.", "Miss"] as const;
export type UserTitle = (typeof TITLES)[number];

export interface NameValue {
  title: UserTitle | "";
  firstName: string;
  middleName: string;
  lastName: string;
}

export const EMPTY_NAME: NameValue = { title: "", firstName: "", middleName: "", lastName: "" };

/** Title dropdown plus first, middle (optional) and last name. */
export function NameFields({ value, onChange }: { value: NameValue; onChange: (next: NameValue) => void }) {
  const set = (patch: Partial<NameValue>) => onChange({ ...value, ...patch });
  return (
    <div className="grid grid-cols-2 gap-3">
      <Field label="Title">
        <select value={value.title} onChange={(e) => set({ title: e.target.value as UserTitle | "" })} className={INPUT}>
          <option value="">None</option>
          {TITLES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </Field>
      <Field label="First name">
        <input required value={value.firstName} onChange={(e) => set({ firstName: e.target.value })} placeholder="Jane" className={INPUT} />
      </Field>
      <Field label="Middle name">
        <input value={value.middleName} onChange={(e) => set({ middleName: e.target.value })} placeholder="Optional" className={INPUT} />
      </Field>
      <Field label="Last name">
        <input required value={value.lastName} onChange={(e) => set({ lastName: e.target.value })} placeholder="Perera" className={INPUT} />
      </Field>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

export function RoleChip({ role }: { role: Role }) {
  return (
    <span className={`inline-flex items-center text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${ROLE_STYLE[role]}`}>
      {ROLE_LABEL[role]}
    </span>
  );
}

/** Checkbox group for picking one or more roles (in canonical order). */
export function RolePicker({
  value,
  onChange,
  disabled,
  locked = [],
}: {
  value: Role[];
  onChange: (roles: Role[]) => void;
  disabled?: boolean;
  /** Roles that cannot be toggled (e.g. an admin's own admin role). */
  locked?: Role[];
}) {
  const toggle = (r: Role) =>
    onChange(ROLES.filter((x) => (x === r ? !value.includes(r) : value.includes(x))));
  return (
    <div className="grid grid-cols-2 gap-2" role="group" aria-label="Roles">
      {ROLES.map((r) => {
        const off = disabled || locked.includes(r);
        return (
          <label
            key={r}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
              value.includes(r) ? "border-emerald-600 bg-emerald-50/60 text-slate-900" : "border-slate-200 bg-white text-slate-700"
            } ${off ? "opacity-60 cursor-not-allowed" : "cursor-pointer hover:border-slate-300"}`}
          >
            <input
              type="checkbox"
              className="accent-emerald-700"
              checked={value.includes(r)}
              disabled={off}
              onChange={() => toggle(r)}
            />
            {ROLE_LABEL[r]}
          </label>
        );
      })}
    </div>
  );
}

type Tone = "verified" | "caution" | "defect" | "neutral";
const TONE: Record<Tone, string> = {
  verified: "bg-emerald-50 text-emerald-800 border-emerald-200",
  caution: "bg-amber-50 text-amber-800 border-amber-200",
  defect: "bg-rose-50 text-rose-700 border-rose-200",
  neutral: "bg-slate-50 text-slate-600 border-slate-200",
};
const DOT: Record<Tone, string> = {
  verified: "bg-emerald-600",
  caution: "bg-amber-500",
  defect: "bg-rose-600",
  neutral: "bg-slate-400",
};

export function Chip({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${TONE[tone]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${DOT[tone]}`} />
      {children}
    </span>
  );
}

export function Avatar({ name }: { name: string }) {
  const initials = name
    .replace(/^(Dr|Prof|Mr|Mrs|Ms|Miss)\.?\s+/i, "")
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join("");
  return (
    <div className="w-8 h-8 shrink-0 rounded-full bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center text-[11px] font-bold">
      {initials || "?"}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-slate-500 mt-1">{hint}</span>}
    </label>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
      <div>
        <h2 className="text-xl font-extrabold tracking-tight text-slate-900">{title}</h2>
        <p className="text-xs text-slate-600 mt-1 max-w-2xl">{description}</p>
      </div>
      {action}
    </div>
  );
}

export interface Stat {
  label: string;
  value: number | string;
  warn?: boolean;
  icon: React.ComponentType<{ className?: string }>;
}

export function StatRow({ stats, loaded }: { stats: Stat[]; loaded: boolean }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {stats.map((s) => {
        const Icon = s.icon;
        return (
          <div
            key={s.label}
            className={`rounded-xl border p-4 shadow-xs ${s.warn ? "border-amber-200 bg-amber-50/60" : "border-slate-200/90 bg-white"}`}
          >
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider font-semibold text-slate-500">
              <Icon className={`w-3.5 h-3.5 ${s.warn ? "text-amber-600" : "text-slate-400"}`} />
              {s.label}
            </div>
            <div className={`font-mono text-2xl font-bold mt-1.5 ${s.warn ? "text-amber-800" : "text-slate-900"}`}>
              {loaded ? s.value : "—"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="relative flex-1 min-w-[200px]">
      <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-white border border-slate-200 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-700 focus:ring-1 focus:ring-emerald-700"
      />
    </div>
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; count?: number }[];
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap gap-1 p-1 rounded-lg bg-slate-100 border border-slate-200">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
              active ? "bg-white text-slate-900 shadow-xs border border-slate-200" : "text-slate-600 hover:text-slate-900 border border-transparent"
            }`}
          >
            {o.label}
            {o.count !== undefined && <span className="ml-1.5 font-mono text-[11px] text-slate-500">{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white rounded-xl border border-slate-200/90 shadow-xs ${className}`}>{children}</div>;
}

export function TableState({ loaded, error, empty, colSpan }: { loaded: boolean; error: string | null; empty: string | null; colSpan: number }) {
  let content: React.ReactNode = null;
  if (error) content = <span className="text-rose-700">{error}</span>;
  else if (!loaded)
    content = (
      <span className="inline-flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading…
      </span>
    );
  else if (empty) content = empty;
  if (!content) return null;
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-10 text-center text-xs text-slate-500">
        {content}
      </td>
    </tr>
  );
}

export const TH = "text-left text-[11px] font-semibold uppercase tracking-wider text-slate-500 px-4 py-2.5";

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

export function Modal({
  open,
  title,
  description,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    // Focus the first field (or the Cancel button for confirmations).
    panelRef.current?.querySelector<HTMLElement>("input, select, textarea, [data-autofocus]")?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-slate-900/30" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full sm:max-w-lg bg-white rounded-t-xl sm:rounded-xl border border-slate-200 shadow-xl max-h-[90vh] flex flex-col"
      >
        <div className="px-5 pt-5 pb-4 border-b border-slate-100 flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">{title}</h3>
            {description && <p className="text-xs text-slate-600 mt-1">{description}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="p-1 rounded-md text-slate-500 hover:bg-slate-100">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-5 py-4 space-y-4 overflow-y-auto">{children}</div>
        <div className="px-5 py-4 border-t border-slate-100 bg-slate-50/60 rounded-b-xl flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          {footer}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toasts
// ---------------------------------------------------------------------------

interface Toast {
  id: number;
  kind: "ok" | "error";
  text: string;
}

const ToastContext = createContext<(kind: Toast["kind"], text: string) => void>(() => {});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback(
    (kind: Toast["kind"], text: string) => {
      const id = Date.now() + Math.random();
      setToasts((t) => [...t.slice(-2), { id, kind, text }]);
      setTimeout(() => dismiss(id), kind === "error" ? 8000 : 5000);
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 left-4 sm:left-auto z-[70] flex flex-col gap-2 sm:w-96">
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.kind === "error" ? "alert" : "status"}
            className={`flex items-start gap-2.5 rounded-xl border px-4 py-3 text-xs shadow-xl bg-white ${
              t.kind === "ok" ? "border-emerald-200 text-emerald-900" : "border-rose-200 text-rose-800"
            }`}
          >
            {t.kind === "ok" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-700 shrink-0" />
            )}
            <span className="flex-1">{t.text}</span>
            <button onClick={() => dismiss(t.id)} aria-label="Dismiss" className="text-slate-400 hover:text-slate-700">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
