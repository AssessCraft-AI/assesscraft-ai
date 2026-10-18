"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, CheckCheck } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export interface AppNotification {
  id: string;
  type: "submitted_for_moderation" | "moderation_approved" | "moderation_changes_requested" | "moderator_assigned" | "module_assigned";
  title: string;
  message: string;
  assessmentId?: string | null;
  actorName?: string | null;
  read: boolean;
  createdAt: string;
}

// Each poll reads every notification of the user from Firestore; refresh on tab focus covers the gap.
const POLL_MS = 120_000;

const DOT: Record<AppNotification["type"], string> = {
  submitted_for_moderation: "bg-amber-500",
  moderation_approved: "bg-emerald-600",
  moderation_changes_requested: "bg-red-500",
  moderator_assigned: "bg-sky-500",
  module_assigned: "bg-sky-500",
};

function timeAgo(iso: string): string {
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return "just now";
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

export function NotificationBell() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuth();
  // Tagged with the account that loaded it so a previous user's list never shows after a switch.
  const [loaded, setLoaded] = useState<{ owner: string; items: AppNotification[] }>({ owner: "", items: [] });
  const items = loaded.owner === user.email ? loaded.items : [];
  const setItems = (update: (prev: AppNotification[]) => AppNotification[]) =>
    setLoaded((prev) => ({ ...prev, items: update(prev.items) }));
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const owner = user.email;
      const list = await apiRequest<AppNotification[]>("/notifications");
      setLoaded({ owner, items: list });
    } catch {
      // Transient: keep the last list; the next poll retries.
    }
  }, [user.email]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void load();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [isAuthenticated, load]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const unread = items.filter((n) => !n.read).length;

  const openItem = async (n: AppNotification) => {
    setOpen(false);
    if (!n.read) {
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, read: true } : x)));
      void apiRequest(`/notifications/${n.id}/read`, { method: "POST" }).catch(() => {});
    }
    if (n.assessmentId) router.push(`/assessments/${n.assessmentId}`);
  };

  const markAll = async () => {
    setItems((prev) => prev.map((x) => ({ ...x, read: true })));
    await apiRequest("/notifications/read-all", { method: "POST" }).catch(() => {});
  };

  if (!isAuthenticated) return null;

  return (
    <div className="relative" ref={panelRef}>
      <button
        id="notifications-btn"
        onClick={() => {
          setOpen(!open);
          if (!open) void load();
        }}
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        className="relative w-9 h-9 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300 flex items-center justify-center transition-colors"
      >
        <Bell className="w-4 h-4 text-slate-600" />
        {unread > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          id="notifications-panel"
          className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl bg-white border border-slate-200 shadow-xl z-50 overflow-hidden"
        >
          <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Notifications</span>
            {unread > 0 && (
              <button
                onClick={markAll}
                className="text-xs text-emerald-700 hover:text-emerald-800 font-medium flex items-center gap-1"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-3 py-6 text-center text-xs text-slate-500">You&apos;re all caught up.</p>
            ) : (
              items.map((n) => (
                <button
                  key={n.id}
                  onClick={() => openItem(n)}
                  className={`w-full text-left px-3 py-2.5 border-b border-slate-50 last:border-0 hover:bg-slate-50 flex gap-2.5 ${
                    n.read ? "" : "bg-emerald-50/40"
                  }`}
                >
                  <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${n.read ? "bg-slate-300" : DOT[n.type]}`} />
                  <span className="min-w-0">
                    <span className={`block text-xs ${n.read ? "text-slate-700" : "text-slate-900 font-semibold"}`}>
                      {n.title}
                    </span>
                    <span className="block text-xs text-slate-600 mt-0.5 break-words">{n.message}</span>
                    <span className="block text-[11px] text-slate-400 mt-1">{timeAgo(n.createdAt)}</span>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
