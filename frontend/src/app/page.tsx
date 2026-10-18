"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiRequest } from "@/lib/api";
import { Modal, BTN_DANGER, BTN_SECONDARY } from "@/components/admin/ui";
import {
  Sparkles,
  BookOpen,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  AlertCircle,
  FileText,
  Server,
  Cpu,
  UserCheck,
  Mail,
  Trash2,
} from "lucide-react";

interface ContactSummary {
  uid: string;
  email: string;
  displayName: string;
  institution?: string | null;
}

interface ModuleContacts {
  courseId: string;
  code: string;
  title: string;
  owner?: ContactSummary | null;
  moderator?: ContactSummary | null;
}

interface MyContacts {
  // Modules the user owns (each with its moderator) and moderates (each with its owner).
  modules: ModuleContacts[];
  lecturers: ContactSummary[];
}

interface HealthData {
  status: string;
  app: string;
  region: string;
  model: string;
  agentRuntime: string;
  datastore: string;
  llmConfigured?: boolean;
}

interface AssessmentData {
  id: string;
  courseId: string;
  title: string;
  status: string;
  totalMarks: number;
  createdAt: string;
  moderatorUid?: string | null;
  createdBy?: string | null;
  createdByUid?: string | null;
}

// Mirrors the backend: a paper in moderation or approved cannot be deleted.
const LOCKED_STATUSES = ["in_moderation", "approved"];

interface CourseData {
  id: string;
  code: string;
  title: string;
  confirmed: boolean;
  clos: Array<{ id: string; text: string }>;
  topics: Array<{ id: string; name: string }>;
}

export default function DashboardPage() {
  const { user, isAdmin, isLecturer, isModerator } = useAuth();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [courses, setCourses] = useState<CourseData[]>([]);
  const [assessments, setAssessments] = useState<AssessmentData[]>([]);
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contacts, setContacts] = useState<MyContacts | null>(null);
  const [toDelete, setToDelete] = useState<AssessmentData | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const canDelete = (a: AssessmentData) =>
    isLecturer &&
    (a.createdByUid ? a.createdByUid === user.uid : a.createdBy === user.email) &&
    !LOCKED_STATUSES.includes(a.status);

  const closeDelete = () => {
    if (deleting) return;
    setToDelete(null);
    setDeleteError(null);
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await apiRequest(`/assessments/${toDelete.id}`, { method: "DELETE" });
      setAssessments((prev) => prev.filter((a) => a.id !== toDelete.id));
      setToDelete(null);
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete the assessment");
    } finally {
      setDeleting(false);
    }
  };

  // Admins manage users rather than papers, unless they also lecture or moderate.
  const adminOnly = isAdmin && !isLecturer && !isModerator;
  useEffect(() => {
    if (adminOnly) router.replace("/admin/users");
  }, [adminOnly, router]);

  useEffect(() => {
    if (!isLecturer && !isModerator) return;
    apiRequest<MyContacts>("/me/contacts").then(setContacts).catch(() => setContacts(null));
  }, [isLecturer, isModerator]);

  // A user with both roles gets both cards: the modules they own and the ones they moderate.
  const ownedModules = contacts?.modules.filter((m) => m.owner?.uid === user.uid) ?? [];
  const moderatedModules = contacts?.modules.filter((m) => m.moderator?.uid === user.uid) ?? [];
  // Papers are written only for modules the user lectures (the backend enforces the same).
  const canCreate = isLecturer && ownedModules.length > 0;
  const noModuleHint = "You are not the lecturer of any module yet";
  const awaitingMyReview = assessments.filter((a) => a.status === "in_moderation" && a.moderatorUid === user.uid).length;

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [healthRes, coursesRes, assessmentsRes] = await Promise.allSettled([
          apiRequest<HealthData>("/health"),
          apiRequest<CourseData[]>("/courses"),
          apiRequest<AssessmentData[]>("/assessments"),
        ]);
        if (assessmentsRes.status === "fulfilled") {
          setAssessments([...assessmentsRes.value].sort((a, b) => b.createdAt.localeCompare(a.createdAt)));
        }

        if (healthRes.status === "fulfilled") {
          setHealth(healthRes.value);
        }
        if (coursesRes.status === "fulfilled") {
          setCourses(coursesRes.value);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const firstName = user.displayName || "there";
  const liveAgents = health?.status === "healthy" && health.llmConfigured === true;

  const statusStyle = (status: string) =>
    status === "approved"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : status === "changes_requested"
      ? "bg-red-50 text-red-700 border-red-200"
      : status === "draft"
      ? "bg-slate-100 text-slate-700 border-slate-200"
      : "bg-amber-50 text-amber-700 border-amber-200";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header matching Figma Screen 1 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Welcome back, <span className="text-emerald-600 font-bold">{firstName}</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Overview of your assessment sets, lifecycle states and quality metrics.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {canCreate ? (
            <Link
              href="/assessments/new"
              id="start-assessment-btn"
              className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-medium text-sm shadow-xs transition-all"
            >
              <Sparkles className="w-4 h-4" />
              <span>+ New assessment</span>
            </Link>
          ) : (
            <span
              id="start-assessment-btn"
              aria-disabled="true"
              title={noModuleHint}
              className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg bg-emerald-700 text-white font-medium text-sm shadow-xs opacity-50 cursor-not-allowed"
            >
              <Sparkles className="w-4 h-4" />
              <span>+ New assessment</span>
            </span>
          )}
        </div>
      </div>

      {/* Stat cards (live counts) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {[
          { value: courses.length, label: "Courses" },
          { value: assessments.length, label: "Assessments" },
          { value: assessments.filter((a) => a.status === "approved").length, label: "Approved papers" },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs hover:border-slate-300 transition-all">
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight">{loading ? "–" : stat.value}</div>
            <div className="text-sm text-slate-500 font-medium mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Moderation contacts shared by the admin */}
      {isLecturer && contacts && (
        <div id="my-moderator-card" className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <UserCheck className="w-4 h-4 text-amber-700" />
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Moderators for your modules</div>
          </div>
          {ownedModules.length === 0 ? (
            <p className="text-sm text-slate-500">You are not the lecturer for any module yet. An administrator assigns modules and their moderators.</p>
          ) : (
            <ul className="grid sm:grid-cols-2 gap-2">
              {ownedModules.map((m) => (
                <li key={m.courseId} className="rounded-lg border border-slate-200 px-3 py-2 min-w-0">
                  <div className="text-xs">
                    <span className="font-mono font-bold text-slate-900">{m.code}</span>
                    <span className="text-slate-600"> · {m.title}</span>
                  </div>
                  {m.moderator ? (
                    <div className="mt-1">
                      <div className="text-sm font-semibold text-slate-900">{m.moderator.displayName}</div>
                      <a href={`mailto:${m.moderator.email}`} className="text-xs text-emerald-700 hover:underline inline-flex items-center gap-1 break-all">
                        <Mail className="w-3.5 h-3.5" /> {m.moderator.email}
                      </a>
                    </div>
                  ) : (
                    <p className="mt-1 text-xs text-amber-800">No moderator yet. Papers for this module cannot be submitted until an administrator assigns one.</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {isModerator && contacts && (
        <div id="my-lecturers-card" className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Modules you moderate</div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
              {awaitingMyReview} awaiting your review
            </span>
          </div>
          {moderatedModules.length === 0 ? (
            <p className="text-sm text-slate-500">No modules are assigned to you yet.</p>
          ) : (
            <ul className="grid sm:grid-cols-2 gap-2">
              {moderatedModules.map((m) => (
                <li key={m.courseId} className="text-sm rounded-lg border border-slate-200 px-3 py-2 min-w-0">
                  <div className="text-xs">
                    <span className="font-mono font-bold text-slate-900">{m.code}</span>
                    <span className="text-slate-600"> · {m.title}</span>
                  </div>
                  {m.owner ? (
                    <>
                      <div className="font-semibold text-slate-900 mt-1">{m.owner.displayName}</div>
                      <a href={`mailto:${m.owner.email}`} className="text-xs text-emerald-700 hover:underline break-all">{m.owner.email}</a>
                    </>
                  ) : (
                    <p className="mt-1 text-xs text-slate-500">No lecturer assigned yet.</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Recent Assessments Section matching Figma Screen 1 */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">
            Recent assessments
          </h2>
        </div>

        <div className="divide-y divide-slate-100">
          {!loading && assessments.length === 0 && (
            <div className="p-5 text-sm text-slate-500">
              No assessments yet. Open one of your modules and upload its materials first, then start a new assessment.
            </div>
          )}
          {assessments.slice(0, 8).map((a) => (
            <div key={a.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/70 transition-colors">
              <div className="space-y-1">
                <div className="flex items-center space-x-3">
                  <span className="text-sm font-semibold text-slate-900">{a.title}</span>
                  <span className={`inline-flex items-center text-xs px-2.5 py-0.5 rounded-full font-medium border ${statusStyle(a.status)}`}>
                    {a.status.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="text-xs text-slate-500 flex items-center space-x-3">
                  <span>{a.courseId} • {a.totalMarks} marks</span>
                  <span>•</span>
                  <span>{new Date(a.createdAt).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/assessments/${a.id}`}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-xs font-medium text-slate-700 border border-slate-200 shadow-xs transition-colors"
                >
                  Inspect Paper Set
                </Link>
                {canDelete(a) && (
                  <button
                    type="button"
                    onClick={() => setToDelete(a)}
                    aria-label={`Delete ${a.title}`}
                    title="Delete assessment"
                    className="p-1.5 rounded-lg bg-white hover:bg-rose-50 text-slate-500 hover:text-rose-700 border border-slate-200 hover:border-rose-200 shadow-xs transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4" aria-hidden />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <Modal
        open={!!toDelete}
        title="Delete assessment?"
        description="This permanently deletes the paper with its blueprint, questions, review flags and versions. It cannot be undone."
        onClose={closeDelete}
        footer={
          <>
            <button type="button" data-autofocus onClick={closeDelete} disabled={deleting} className={BTN_SECONDARY}>
              Cancel
            </button>
            <button type="button" onClick={handleDelete} disabled={deleting} className={BTN_DANGER}>
              {deleting ? "Deleting..." : "Delete assessment"}
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-700">
          <span className="font-semibold">{toDelete?.title}</span> · {toDelete?.courseId}
        </p>
        {deleteError && <p className="text-xs text-rose-700">{deleteError}</p>}
      </Modal>

      {/* System Status Banner (Clean Minimal) */}
      <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200/90 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="relative">
            {liveAgents && <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping absolute" />}
            <div className={`w-2.5 h-2.5 rounded-full ${liveAgents ? "bg-emerald-700" : "bg-amber-500"}`} />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold text-slate-900">
                Agents
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                  liveAgents ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"
                }`}
              >
                {liveAgents ? "Live: LLM connected" : health ? "Offline fallback: LLM not connected" : "Backend unreachable"}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Google ADK agents · Gemini 3.1 Flash Lite via OpenRouter · OR-Tools CP-SAT solver
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-xs text-slate-500">
          <div className="flex items-center space-x-1.5">
            <Server className="w-3.5 h-3.5 text-slate-500" />
            <span>Region: <strong className="text-slate-700">{health?.region || "—"}</strong></span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Cpu className="w-3.5 h-3.5 text-emerald-600" />
            <span>Model: <strong className="text-slate-700">{health?.model || "—"}</strong></span>
          </div>
        </div>
      </div>

      {/* Courses Section */}
      <div id="courses" className="space-y-4 scroll-mt-24">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <BookOpen className="w-4 h-4 text-emerald-600" />
            <span>Active Courses & Knowledge Stores</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {courses.map((course) => (
            <div
              key={course.id}
              id={`course-card-${course.code.toLowerCase()}`}
              className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-4 hover:border-slate-300 transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {course.code}
                    </span>
                    {course.confirmed && (
                      <span className="text-xs text-emerald-700 flex items-center space-x-1 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>CLOs Confirmed</span>
                      </span>
                    )}
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mt-1">
                    {course.title}
                  </h3>
                </div>

                <Link
                  href={`/courses/${course.code}`}
                  id={`open-course-${course.code.toLowerCase()}`}
                  className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center space-x-1.5 transition-colors border border-slate-200 shadow-xs"
                >
                  <span>Open Course</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                </Link>
              </div>

              <div className="grid grid-cols-3 gap-3 py-3 border-y border-slate-100 text-center">
                <div>
                  <div className="text-base font-bold text-slate-900">{course.clos?.length ?? 0}</div>
                  <div className="text-[11px] text-slate-500">Learning Outcomes</div>
                </div>
                <div>
                  <div className="text-base font-bold text-slate-900">{course.topics?.length ?? 0}</div>
                  <div className="text-[11px] text-slate-500">Syllabus Topics</div>
                </div>
                <div>
                  <div className="text-base font-bold text-slate-900">{assessments.filter((a) => a.courseId === course.id).length}</div>
                  <div className="text-[11px] text-slate-500">Assessments</div>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{course.clos?.length ? "Outcomes extracted" : "Upload materials to extract outcomes"}</span>
                <Link
                  href={`/courses/${course.code}?assistant=true`}
                  className="text-emerald-700 hover:text-emerald-800 font-medium flex items-center space-x-1"
                >
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Knowledge Assistant</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
