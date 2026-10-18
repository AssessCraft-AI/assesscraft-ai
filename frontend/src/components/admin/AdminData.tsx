"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useAuth, type Role } from "@/context/AuthContext";
import type { UserTitle } from "@/components/admin/ui";
import { apiRequest } from "@/lib/api";

export interface AdminUser {
  uid: string;
  email: string;
  /** Full name as shown, including the title ("Dr. Amali Perera"). */
  displayName: string;
  title?: UserTitle | null;
  firstName?: string | null;
  middleName?: string | null;
  lastName?: string | null;
  /** Primary role (the first of `roles`). */
  role: Role;
  roles: Role[];
  institution?: string;
  disabled: boolean;
  authProvisioned: boolean;
  createdAt: string;
}

export interface Module {
  id: string;
  code: string;
  title: string;
  ownerUid: string;
  /** The moderator who reviews this module's papers (set per module, not per lecturer). */
  moderatorUid?: string | null;
  confirmed: boolean;
  clos: unknown[];
  topics: unknown[];
  updatedAt: string;
}

interface AdminDataValue {
  users: AdminUser[];
  modules: Module[];
  loaded: boolean;
  error: string | null;
  reload: () => Promise<void>;
  byUid: Record<string, AdminUser>;
  lecturers: AdminUser[];
  moderators: AdminUser[];
  /** Everyone who can be picked as a module's moderator: moderators, plus lecturers (who gain the role when picked). */
  moderatorCandidates: AdminUser[];
  /** Number of modules owned by each lecturer uid. */
  modulesByOwner: Record<string, number>;
  /** Number of modules moderated by each moderator uid. */
  modulesByModerator: Record<string, number>;
  /** The module's owner while they are still an active lecturer. */
  ownerOf: (m: Module) => AdminUser | undefined;
  /** The module's moderator while they are still an active moderator. */
  moderatorOf: (m: Module) => AdminUser | undefined;
}

const AdminDataContext = createContext<AdminDataValue | undefined>(undefined);

/** Every role a user holds; older records only carry `role`. */
export const rolesOf = (u: Pick<AdminUser, "role" | "roles">): Role[] => (u.roles?.length ? u.roles : [u.role]);

export function errText(err: unknown): string {
  return ((err as Error)?.message || "Request failed").replace(/^API Error \(\d+\): /, "");
}

const fetchAll = () =>
  Promise.all([apiRequest<AdminUser[]>("/admin/users"), apiRequest<Module[]>("/courses")]);

/** Loads users and modules once for every admin page, so switching tabs does not refetch. */
export function AdminDataProvider({ children }: { children: React.ReactNode }) {
  const { isAdmin, loading: authLoading } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [modules, setModules] = useState<Module[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apply = useCallback(([userList, moduleList]: [AdminUser[], Module[]]) => {
    setUsers(userList);
    setModules([...moduleList].sort((a, b) => a.code.localeCompare(b.code)));
    setError(null);
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    let live = true;
    fetchAll()
      .then((data) => live && apply(data))
      .catch((err) => {
        if (!live) return;
        setError(errText(err));
        setLoaded(true);
      });
    return () => {
      live = false;
    };
  }, [authLoading, isAdmin, apply]);

  const reload = useCallback(async () => {
    try {
      apply(await fetchAll());
    } catch (err) {
      setError(errText(err));
    }
  }, [apply]);

  const value = useMemo<AdminDataValue>(() => {
    const byUid = Object.fromEntries(users.map((u) => [u.uid, u]));
    const active = (uid: string | null | undefined, role: Role) =>
      uid && byUid[uid] && rolesOf(byUid[uid]).includes(role) && !byUid[uid].disabled ? byUid[uid] : undefined;
    const tally = (key: (m: Module) => string | null | undefined) => {
      const out: Record<string, number> = {};
      for (const m of modules) {
        const k = key(m);
        if (k) out[k] = (out[k] || 0) + 1;
      }
      return out;
    };
    return {
      users,
      modules,
      loaded,
      error,
      reload,
      byUid,
      lecturers: users.filter((u) => rolesOf(u).includes("lecturer") && !u.disabled),
      moderators: users.filter((u) => rolesOf(u).includes("moderator") && !u.disabled),
      moderatorCandidates: users
        .filter((u) => !u.disabled && (rolesOf(u).includes("moderator") || rolesOf(u).includes("lecturer")))
        .sort((a, b) => a.displayName.localeCompare(b.displayName)),
      modulesByOwner: tally((m) => m.ownerUid),
      modulesByModerator: tally((m) => m.moderatorUid),
      ownerOf: (m) => active(m.ownerUid, "lecturer"),
      moderatorOf: (m) => active(m.moderatorUid, "moderator"),
    };
  }, [users, modules, loaded, error, reload]);

  return <AdminDataContext.Provider value={value}>{children}</AdminDataContext.Provider>;
}

export function useAdminData(): AdminDataValue {
  const ctx = useContext(AdminDataContext);
  if (!ctx) throw new Error("useAdminData must be used inside AdminDataProvider");
  return ctx;
}
