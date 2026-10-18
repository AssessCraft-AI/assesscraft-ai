"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, ArrowRight, Loader2, Lock, Mail } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { signIn, isAuthenticated, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && isAuthenticated) router.replace("/");
  }, [authLoading, isAuthenticated, router]);

  const friendlyError = (err: unknown) => {
    const code = (err as { code?: string })?.code || "";
    if (code.includes("invalid-credential") || code.includes("wrong-password") || code.includes("user-not-found")) {
      return "Incorrect email or password.";
    }
    if (code.includes("too-many-requests")) return "Too many attempts. Please wait and try again.";
    if (code.includes("operation-not-allowed")) {
      return "Email/password sign-in is not enabled for this project. An administrator must enable it in Firebase Authentication.";
    }
    if (code.includes("user-disabled")) return "This account has been disabled. Contact your administrator.";
    return (err as Error)?.message || "Sign-in failed.";
  };

  const handleCustomLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setLoading(false);
    }
  };

  const fieldClass =
    "w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-white border border-slate-200 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 transition-colors";

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-slate-50 px-4 py-16">
      {/* Soft mint-to-sky wash behind the sign-in sheet */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(85%_100%_at_15%_35%,#c2f1d8_0%,transparent_72%),radial-gradient(80%_95%_at_92%_78%,#cde5f7_0%,transparent_72%),radial-gradient(40%_40%_at_70%_15%,#f1f7fb_0%,transparent_70%)]"
      />

      <div className="relative w-full max-w-[560px] text-center motion-safe:animate-[login-rise_0.9s_cubic-bezier(0.16,1,0.3,1)_both]">
        <div className="mx-auto w-[72px] h-[72px] rounded-[20px] bg-emerald-700 flex items-center justify-center text-white shadow-[0_10px_24px_-10px_rgb(6_78_59/0.55)]">
          <Sparkles className="w-9 h-9" strokeWidth={1.75} />
        </div>
        <h1 className="mt-7 text-[44px] sm:text-[56px] leading-[1.05] font-bold tracking-[-0.03em] text-slate-900">
          AssessCraft
        </h1>
        <p className="mt-3 text-[17px] sm:text-[19px] leading-snug text-slate-600">
          Agentic Copilot for Academic Assessment Work
        </p>
        <div className="mt-5 inline-flex items-center px-3.5 py-1 rounded-full text-[13px] font-medium bg-emerald-50/80 text-emerald-800 border border-emerald-200">
          Google Cloud AI Builder Cup 2026 Entry
        </div>

        <div className="mt-10 mx-auto max-w-[440px] rounded-[28px] bg-white/85 backdrop-blur-xl border border-white p-6 sm:p-8 shadow-[0_24px_60px_-24px_rgb(15_23_42/0.25),0_2px_6px_-2px_rgb(15_23_42/0.06)]">
          <p className="text-[15px] sm:text-[16px] text-slate-600">
            Sign in with your institutional account
          </p>

          <form onSubmit={handleCustomLogin} className="mt-6 text-left">
            <div className="space-y-4">
              <div>
                <label htmlFor="login-email-input" className="block text-xs font-semibold text-slate-700 mb-1">
                  Institutional Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    id="login-email-input"
                    type="email"
                    required
                    autoComplete="username"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="lecturer@university.edu"
                    aria-invalid={!!error}
                    aria-describedby={error ? "login-error" : undefined}
                    className={fieldClass}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="login-password-input" className="block text-xs font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    id="login-password-input"
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    aria-invalid={!!error}
                    aria-describedby={error ? "login-error" : undefined}
                    className={fieldClass}
                  />
                </div>
              </div>
            </div>

            <button
              id="login-submit-btn"
              type="submit"
              disabled={loading}
              className="mt-6 w-full h-14 rounded-full bg-emerald-700 hover:bg-emerald-800 active:scale-[0.99] text-white text-[17px] font-semibold flex items-center justify-center gap-2 shadow-[0_8px_20px_-10px_rgb(6_78_59/0.6)] transition-[background-color,transform] duration-200 ease-out disabled:opacity-60 disabled:cursor-default cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-[18px] h-[18px] animate-spin" />
                  <span>Signing in…</span>
                </>
              ) : (
                <>
                  <span>Sign In to Workspace</span>
                  <ArrowRight className="w-[18px] h-[18px]" strokeWidth={2.25} />
                </>
              )}
            </button>

            {error && (
              <p id="login-error" role="alert" className="mt-4 text-[14px] leading-snug text-rose-700 text-center">
                {error}
              </p>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
