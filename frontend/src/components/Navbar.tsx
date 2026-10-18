"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  Sparkles,
  BookOpen,
  BarChart3,
  UserCheck,
  ShieldAlert,
  ChevronDown,
  LogOut,
  Users,
  KeyRound,
  Library,
  Link2,
} from "lucide-react";
import { NotificationBell } from "@/components/NotificationBell";

export function Navbar() {
  const pathname = usePathname();
  const { user, role, roles, logout, isAuthenticated } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const heldRoles = mounted && isAuthenticated ? roles : [];
  const isAdminUser = heldRoles.includes("admin");
  // Admins who also lecture or moderate get the paper links as well as the admin ones.
  const doesPaperWork = heldRoles.some((r) => r !== "admin") || !isAdminUser;
  const navLinks = [
    ...(doesPaperWork
      ? [
          { href: "/", label: "Dashboard", icon: BookOpen },
          { href: "/assessments/new", label: "New assessment", icon: Sparkles },
        ]
      : []),
    ...(isAdminUser
      ? [
          { href: "/admin/users", label: "Users", icon: Users },
          { href: "/admin/modules", label: "Modules", icon: Library },
          { href: "/admin/assignments", label: "Assignments", icon: Link2 },
        ]
      : []),
    { href: "/analytics", label: "Analytics", icon: BarChart3 },
  ];

  const getRoleBadge = (currentRole: string) => {
    switch (currentRole) {
      case "admin":
        return {
          bg: "bg-slate-100 text-slate-900 border-slate-300",
          label: "Administrator",
          icon: KeyRound,
        };
      case "moderator":
        return {
          bg: "bg-amber-50 text-amber-700 border-amber-200",
          label: "External Moderator",
          icon: ShieldAlert,
        };
      default:
        return {
          bg: "bg-sky-50 text-sky-700 border-sky-200",
          label: "Lecturer",
          icon: UserCheck,
        };
    }
  };

  const activeUser = mounted && isAuthenticated ? user : null;
  const effectiveRole = mounted && isAuthenticated ? role : "lecturer";
  const badge = getRoleBadge(effectiveRole);
  const RoleIcon = badge.icon;
  const badgeLabel = heldRoles.length > 1 ? heldRoles.map((r) => getRoleBadge(r).label).join(" · ") : badge.label;

  // The login page is a standalone screen without the app header
  if (pathname === "/login") return null;

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand */}
        <div className="flex items-center space-x-6">
          <Link href="/" id="nav-brand" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-lg bg-emerald-700 flex items-center justify-center text-white shadow-sm shadow-emerald-600/20 group-hover:bg-emerald-800 transition-colors">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-slate-900 group-hover:text-emerald-700 transition-colors">
                  AssessCraft
                </span>
                <span className="text-[11px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  AI
                </span>
              </div>
              <p className="hidden sm:block text-[11px] text-slate-500 font-medium">Academic Assessment Copilot</p>
            </div>
          </Link>

          {/* Nav Links */}
          <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-slate-200">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = item.href === "/" ? pathname === "/" || pathname.startsWith("/assessments/") && pathname !== "/assessments/new" || pathname.startsWith("/courses/") : pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  id={`nav-link-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-emerald-50 text-emerald-800 border border-emerald-200/80 shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-emerald-600" : "text-slate-500"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right: Persona / Auth Switcher */}
        <div className="flex items-center space-x-3">
          <NotificationBell />
          <div className="relative">
            <button
              id="user-persona-btn"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center space-x-3 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-all text-left shadow-xs"
            >
              <div className="w-7 h-7 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-800 flex items-center justify-center font-bold text-xs">
                {activeUser?.displayName ? activeUser.displayName.charAt(0) : "U"}
              </div>
              <div className="hidden sm:block text-left">
                <div className="text-xs font-semibold text-slate-800">
                  {activeUser ? activeUser.displayName : ""}
                </div>
                <div className="text-[11px] text-slate-500">{activeUser ? activeUser.email : ""}</div>
              </div>
              <span
                className={`hidden sm:inline-flex items-center space-x-1 text-xs px-2 py-0.5 rounded-full border font-medium ${badge.bg}`}
              >
                <RoleIcon className="w-3 h-3" />
                <span>{badgeLabel}</span>
              </span>
              <ChevronDown className="w-4 h-4 text-slate-500" />
            </button>

            {dropdownOpen && (
              <div
                id="persona-dropdown"
                className="absolute right-0 mt-2 w-64 rounded-xl bg-white border border-slate-200 shadow-xl py-2 z-50 text-slate-800"
              >
                <div>
                  <button
                    id="nav-sign-out"
                    onClick={() => {
                      setDropdownOpen(false);
                      void logout();
                    }}
                    className="w-full text-left px-3 py-2 text-xs flex items-center space-x-2 text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  >
                    <LogOut className="w-3.5 h-3.5 text-slate-500" />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile nav: the desktop links are hidden below md */}
      <nav className="md:hidden flex gap-1 overflow-x-auto px-4 pb-2 -mt-1">
        {navLinks.map((item) => {
          const Icon = item.icon;
          const isActive = item.href === "/" ? pathname === "/" || pathname.startsWith("/assessments/") && pathname !== "/assessments/new" || pathname.startsWith("/courses/") : pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap border ${
                isActive
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200/80"
                  : "text-slate-600 border-transparent hover:bg-slate-100"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? "text-emerald-600" : "text-slate-500"}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
