"use client";

import React from "react";
import { ShieldAlert, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AdminDataProvider } from "@/components/admin/AdminData";
import { ToastProvider } from "@/components/admin/ui";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isAdmin, loading } = useAuth();
  const blocked = loading || !isAdmin;

  // The pages stay mounted (so Next can validate the segment) but hidden until the user is a confirmed admin.
  // AdminDataProvider only fetches once isAdmin is true, so a hidden page loads nothing.
  return (
    <AdminDataProvider>
      <ToastProvider>
        {loading ? (
          <div className="max-w-7xl mx-auto px-4 py-20 flex justify-center text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin" />
          </div>
        ) : !isAdmin ? (
          <div className="max-w-xl mx-auto px-4 py-20 text-center">
            <ShieldAlert className="w-10 h-10 text-amber-600 mx-auto mb-3" />
            <h1 className="text-xl font-bold text-slate-900">Administrators only</h1>
            <p className="text-sm text-slate-600 mt-2">
              Users, modules and moderator assignments are managed by an administrator.
            </p>
          </div>
        ) : null}
        <div hidden={blocked} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          {children}
        </div>
      </ToastProvider>
    </AdminDataProvider>
  );
}
