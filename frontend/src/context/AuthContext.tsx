"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
} from "firebase/auth";
import { UserRole, UserSession, apiRequest, getStoredUser } from "@/lib/api";
import { getFirebaseAuth, isDemoLoginEnabled } from "@/lib/firebase";

export type Role = UserRole;

interface AuthContextType {
  user: UserSession;
  /** Primary role, for labels. Use `roles`/`hasRole` for permissions: a user can hold several. */
  role: Role;
  roles: Role[];
  hasRole: (...names: Role[]) => boolean;
  isAuthenticated: boolean;
  loading: boolean;
  demoEnabled: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  loginAsDemo: (role: Role) => void;
  logout: () => Promise<void>;
  isAdmin: boolean;
  isLecturer: boolean;
  isModerator: boolean;
}

const DEMO_PERSONAS: Record<Role, UserSession> = {
  admin: { email: "admin@demo", displayName: "Alex Morgan", role: "admin" },
  lecturer: { email: "lecturer@demo", displayName: "Dr. Samantha Chen", role: "lecturer" },
  moderator: { email: "moderator@demo", displayName: "Prof. David Vance", role: "moderator" },
};

const PLACEHOLDER: UserSession = { email: "", displayName: "", role: "lecturer" };

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface MeResponse {
  uid: string;
  email: string;
  displayName: string;
  role: Role;
  roles?: Role[];
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserSession | null>(null);
  const [loading, setLoading] = useState(true);

  // Resolve the session: Firebase user first (role comes from the server's /me), else a demo persona.
  useEffect(() => {
    const auth = getFirebaseAuth();
    const applyDemoFallback = () => {
      if (isDemoLoginEnabled && localStorage.getItem("assesscraft_user")) {
        setUser(getStoredUser());
      } else {
        setUser(null);
      }
    };

    if (!auth) {
      applyDemoFallback();
      setLoading(false);
      return;
    }
    return onAuthStateChanged(auth, async (fbUser) => {
      if (!fbUser) {
        applyDemoFallback();
        setLoading(false);
        return;
      }
      try {
        const me = await apiRequest<MeResponse>("/me");
        setUser({ uid: me.uid, email: me.email, displayName: me.displayName, role: me.role, roles: me.roles });
      } catch (err) {
        console.error("Could not load profile from API; signing out", err);
        await signOut(auth);
        setUser(null);
      } finally {
        setLoading(false);
      }
    });
  }, []);

  // Route guard: everything except /login requires a session.
  useEffect(() => {
    if (!loading && !user && pathname !== "/login") {
      router.replace("/login");
    }
  }, [loading, user, pathname, router]);

  const signIn = useCallback(async (email: string, password: string) => {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error("Firebase is not configured for this build");
    localStorage.removeItem("assesscraft_user");
    await signInWithEmailAndPassword(auth, email, password);
  }, []);

  const loginAsDemo = useCallback(async (role: Role) => {
    if (!isDemoLoginEnabled) return;
    const persona = DEMO_PERSONAS[role];
    localStorage.setItem("assesscraft_user", JSON.stringify(persona));
    const auth = getFirebaseAuth();
    // A signed-in Firebase user wins in getAuthHeaders, so sign out *before* showing the persona;
    // otherwise the persona's pages would call the API with the previous Firebase user's token.
    if (auth?.currentUser) {
      setLoading(true);
      await signOut(auth);
    }
    setUser(persona);
    setLoading(false);
  }, []);

  const logout = useCallback(async () => {
    localStorage.removeItem("assesscraft_user");
    const auth = getFirebaseAuth();
    if (auth) await signOut(auth);
    setUser(null);
    router.replace("/login");
  }, [router]);

  const current = user ?? PLACEHOLDER;
  const roles: Role[] = user ? (current.roles?.length ? current.roles : [current.role]) : [];
  const hasRole = (...names: Role[]) => names.some((r) => roles.includes(r));

  // Protected pages stay mounted (so Next can validate the segment) but hidden until a session exists.
  // Their API calls wait for auth to resolve (see getAuthHeaders) and fail fast if signed out.
  const gated = !user && pathname !== "/login";

  return (
    <AuthContext.Provider
      value={{
        user: current,
        role: current.role,
        roles,
        hasRole,
        isAuthenticated: Boolean(user),
        loading,
        demoEnabled: isDemoLoginEnabled,
        signIn,
        loginAsDemo,
        logout,
        isAdmin: hasRole("admin"),
        isLecturer: hasRole("lecturer"),
        isModerator: hasRole("moderator"),
      }}
    >
      {gated && (
        <div className="min-h-[60vh] flex items-center justify-center text-sm text-slate-500">Loading…</div>
      )}
      <div hidden={gated}>{children}</div>
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
