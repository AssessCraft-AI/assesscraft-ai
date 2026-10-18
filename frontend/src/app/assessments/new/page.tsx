"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, Check, Loader2, X } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface CourseOption {
  id: string;
  code: string;
  title: string;
  hasOutcomes: boolean;
}

type QType = "mcq" | "short_answer" | "essay";
interface TypeRow {
  enabled: boolean;
  count: number;
  marks: number;
  timeMins: number;
}
type TypeRows = Record<QType, TypeRow>;

const QTYPES: { id: QType; label: string; hint: string }[] = [
  { id: "mcq", label: "Multiple Choice (MCQ)", hint: "4 options, single best answer" },
  { id: "short_answer", label: "Structured", hint: "A few lines, point-based rubric" },
  { id: "essay", label: "Free Response", hint: "Long-form answer, banded rubric" },
];

const OFF: TypeRow = { enabled: false, count: 1, marks: 10, timeMins: 15 };

const totalsOf = (types: TypeRows) => {
  const on = QTYPES.map((q) => types[q.id]).filter((r) => r.enabled);
  return {
    count: on.reduce((n, r) => n + r.count, 0),
    marks: on.reduce((n, r) => n + r.marks, 0),
    mins: on.reduce((n, r) => n + r.timeMins, 0),
  };
};

// Course-neutral presets: the blueprint agent maps them onto the selected course's extracted CLOs and topics.
const SAMPLE_PROMPTS = [
  {
    label: "Final Exam",
    prompt:
      "Cover every course learning outcome. Use MCQs for core concepts and structured questions for higher-order application and analysis.",
    types: {
      mcq: { enabled: true, count: 20, marks: 40, timeMins: 40 },
      short_answer: { enabled: true, count: 10, marks: 60, timeMins: 80 },
      essay: OFF,
    } as TypeRows,
    versions: 2,
  },
  {
    label: "Midterm",
    prompt:
      "Cover only the first half of the syllabus topics, balancing recall with application.",
    types: {
      mcq: { enabled: true, count: 10, marks: 20, timeMins: 20 },
      short_answer: { enabled: true, count: 5, marks: 30, timeMins: 40 },
      essay: OFF,
    } as TypeRows,
    versions: 2,
  },
  {
    label: "Quiz",
    prompt:
      "Test understanding and application of the core topics.",
    types: {
      mcq: { enabled: true, count: 16, marks: 16, timeMins: 20 },
      short_answer: { enabled: true, count: 2, marks: 4, timeMins: 10 },
      essay: OFF,
    } as TypeRows,
    versions: 1,
  },
];

export default function NewAssessmentPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [courses, setCourses] = useState<CourseOption[]>([]);
  const [coursesLoaded, setCoursesLoaded] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [title, setTitle] = useState("");
  const [request, setRequest] = useState(SAMPLE_PROMPTS[0].prompt);
  const [numVersions, setNumVersions] = useState(2);
  const [types, setTypes] = useState<TypeRows>(SAMPLE_PROMPTS[0].types);
  const totals = totalsOf(types);
  // Every question of a type carries the same marks, so marks must split evenly.
  const hasUneven = QTYPES.some((q) => types[q.id].enabled && types[q.id].count > 0 && types[q.id].marks % types[q.id].count !== 0);
  const courseMissingOutcomes = courses.find((c) => c.code === selectedCourse)?.hasOutcomes === false;
  const noModules = coursesLoaded && courses.length === 0;

  const updateType = (id: QType, patch: Partial<TypeRow>) =>
    setTypes((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCourses() {
      try {
        // Papers are written only for modules the user lectures; moderated modules are listed too, so drop them.
        const list = (await apiRequest<any[]>("/courses")).filter((c) => c.ownerUid === user.uid);
        if (list && list.length > 0) {
          setCourses(
            list.map((c) => ({
              id: c.code || c.id,
              code: c.code || c.id,
              title: c.title,
              hasOutcomes: !!c.clos?.length && !!c.topics?.length,
            }))
          );
          setSelectedCourse(list[0].code || list[0].id);
        }
      } catch {
        setCourses([]);
      } finally {
        setCoursesLoaded(true);
      }
    }
    loadCourses();
  }, [user.uid]);

  const handleApplyPreset = (preset: (typeof SAMPLE_PROMPTS)[0]) => {
    setRequest(preset.prompt);
    setTypes(preset.types);
    setNumVersions(preset.versions);
    setTitle(`${selectedCourse} ${preset.label} 2026`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourse) {
      setError("Create a course and upload its materials on the dashboard first.");
      return;
    }
    if (courseMissingOutcomes) {
      setError("This course has no learning outcomes yet. Upload materials and extract outcomes first.");
      return;
    }

    const enabled = QTYPES.filter((q) => types[q.id].enabled);
    if (enabled.length === 0) {
      setError("Please select at least one question type.");
      return;
    }
    if (enabled.some((q) => !(types[q.id].count >= 1 && types[q.id].marks >= 1))) {
      setError("Each selected question type needs at least 1 question and 1 mark.");
      return;
    }
    if (hasUneven) {
      setError("Marks must split evenly across questions for each selected question type.");
      return;
    }
    const typeConfig = enabled.map((q) => ({
      qType: q.id,
      count: types[q.id].count,
      marks: types[q.id].marks,
      timeMins: types[q.id].timeMins,
    }));

    setSubmitting(true);
    setError(null);

    try {
      // 1. Create Assessment
      const assessment = await apiRequest<any>("/assessments", {
        method: "POST",
        body: JSON.stringify({
          courseId: selectedCourse,
          title: title.trim() || `${selectedCourse} Assessment`,
          request: request.trim(),
          numVersions: Number(numVersions),
          typeConfig,
        }),
      });

      const assessmentId = assessment.id;

      // 2. Trigger Blueprint Agent in background
      await apiRequest(`/assessments/${assessmentId}/blueprint`, {
        method: "POST",
      });

      // 3. Redirect to Assessment Workspace with trace drawer open
      router.push(`/assessments/${assessmentId}?trace=open`);
    } catch (err: any) {
      console.error("Creation failed:", err);
      setError(err.message || "Failed to initialize assessment");
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-full py-8">
      <main className="max-w-3xl w-full mx-auto px-4 sm:px-6 space-y-6">
        {/* Breadcrumb & Title matching Screen 2 in Figma */}
        <div>
          <button
            onClick={() => router.push("/")}
            className="text-xs font-semibold text-slate-500 hover:text-emerald-700 transition flex items-center space-x-1 mb-2"
          >
            <span>←</span>
            <span>Back to assessments</span>
          </button>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            New assessment
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Generate a fully aligned assessment from course syllabus, past papers and lecture transcripts using the multi-agent AI pipeline.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} aria-label="Dismiss error" className="text-rose-500 hover:text-rose-700 cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Quick Preset Buttons */}
          <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">Start from a preset</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {SAMPLE_PROMPTS.map((p, idx) => (
                <button
                  type="button"
                  key={idx}
                  onClick={() => handleApplyPreset(p)}
                  className="text-left p-3 rounded-lg bg-slate-50 hover:bg-emerald-50/60 border border-slate-200 hover:border-emerald-300 transition group cursor-pointer"
                >
                  <div className="text-sm font-semibold text-slate-800 group-hover:text-emerald-700 transition">
                    {p.label}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {totalsOf(p.types).marks} Marks • {totalsOf(p.types).mins} Mins
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Core Configuration Panel */}
          <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-5">
            {/* Course Selection */}
            <div>
              <label htmlFor="asm-course" className="block text-xs font-semibold text-slate-700 mb-1.5">
                Course
              </label>
              <select
                id="asm-course"
                value={selectedCourse}
                onChange={(e) => {
                  setSelectedCourse(e.target.value);
                  setTitle(`${e.target.value} Final Examination 2026`);
                }}
                className="w-full bg-white border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 shadow-xs"
              >
                {courses.map((c) => (
                  <option key={c.id} value={c.code}>
                    {c.code} - {c.title}
                  </option>
                ))}
              </select>
              {noModules && (
                <p className="mt-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                  You are not the lecturer of any module yet. Ask an admin to assign you one.
                </p>
              )}
              {courseMissingOutcomes && (
                <p className="mt-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                  This course has no learning outcomes yet.{" "}
                  <Link href={`/courses/${selectedCourse}`} className="font-semibold underline">
                    Upload materials and extract outcomes
                  </Link>{" "}
                  before generating an assessment.
                </p>
              )}
            </div>

            {/* Assessment Title */}
            <div>
              <label htmlFor="asm-title" className="block text-xs font-semibold text-slate-700 mb-1.5">
                Assessment title
              </label>
              <input
                id="asm-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. IT3020 Final Examination 2026"
                className="w-full bg-white border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 shadow-xs"
              />
            </div>

            {/* Natural Language Request: Focus and intent */}
            <div>
              <label htmlFor="asm-request" className="block text-xs font-semibold text-slate-700 mb-1.5">
                Topic focus <span className="font-normal text-slate-500">(optional)</span>
              </label>
              <textarea
                id="asm-request"
                rows={3}
                aria-describedby="asm-request-hint"
                value={request}
                onChange={(e) => setRequest(e.target.value)}
                placeholder="e.g. Emphasise concurrency control and query optimisation; favour application over recall."
                className="w-full bg-white border border-slate-200 rounded-lg p-3.5 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 resize-none font-sans shadow-xs"
              />
              <p id="asm-request-hint" className="mt-1.5 text-xs text-slate-500">
                Steers which topics, outcomes and cognitive levels get the questions. Counts and marks come from the question types below.
              </p>
            </div>

            {/* Per-type question counts, marks and time */}
            <fieldset className="pt-1">
              <legend className="block text-xs font-semibold text-slate-700 mb-2">
                Permitted question types
              </legend>
              <div className="space-y-3">
                {QTYPES.map((q) => {
                  const row = types[q.id];
                  const each = row.count > 0 ? row.marks / row.count : 0;
                  const uneven = row.enabled && each > 0 && !Number.isInteger(each);
                  // Nearest whole per-question mark, used to suggest an even split within input limits.
                  const r = Math.max(1, Math.round(each));
                  const fixCount = row.marks % r === 0 && row.marks / r <= 50 ? row.marks / r : null;
                  const fixMarks = r * row.count <= 1000 ? r * row.count : null;
                  return (
                    <div
                      key={q.id}
                      className={`rounded-lg border px-4 py-3 ${
                        row.enabled ? "bg-white border-emerald-200" : "bg-slate-50 border-slate-200"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start gap-3">
                      <label className="flex items-start gap-2.5 text-sm text-slate-700 cursor-pointer sm:w-56 sm:pt-5 shrink-0">
                        <input
                          type="checkbox"
                          checked={row.enabled}
                          onChange={(e) => updateType(q.id, { enabled: e.target.checked })}
                          className="mt-0.5 w-4 h-4 rounded text-emerald-600 bg-white border-slate-300 focus:ring-emerald-500"
                        />
                        <span>
                          <span className="block font-medium">{q.label}</span>
                          <span className="block text-xs text-slate-500">{q.hint}</span>
                        </span>
                      </label>
                      <div className="flex-1 min-w-0">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {([
                          ["count", "Questions", 1, 50],
                          ["marks", "Marks", 1, 1000],
                          ["timeMins", "Time (mins)", 0, 600],
                        ] as const).map(([field, label, min, max]) => (
                          <div key={field}>
                            <label htmlFor={`${q.id}-${field}`} className="block text-[11px] font-semibold text-slate-500 mb-1">
                              {label}
                            </label>
                            <input
                              id={`${q.id}-${field}`}
                              type="number"
                              min={min}
                              max={max}
                              disabled={!row.enabled}
                              value={row[field]}
                              onChange={(e) => updateType(q.id, { [field]: Number(e.target.value) })}
                              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 shadow-xs disabled:bg-slate-50 disabled:text-slate-400"
                            />
                          </div>
                        ))}
                        <div>
                          <span className="block text-[11px] font-semibold text-slate-500 mb-1">Per question</span>
                          {!row.enabled ? (
                            <p className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-400">—</p>
                          ) : Number.isInteger(each) && each > 0 ? (
                            <p className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-900">
                              {each} mark{each === 1 ? "" : "s"}
                            </p>
                          ) : (
                            <p className="px-3 py-2 rounded-lg bg-amber-50 border border-amber-300 text-sm text-amber-800 flex items-center gap-1.5">
                              <AlertTriangle aria-hidden className="w-3.5 h-3.5 shrink-0" />
                              {each > 0 ? `≈${each.toFixed(1)}` : "—"}
                            </p>
                          )}
                        </div>
                      </div>
                      {uneven && (
                        <div
                          role="status"
                          className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900"
                        >
                          <span className="flex-1 min-w-[12rem]">
                            {row.marks} marks don&apos;t split evenly across {row.count} questions.
                          </span>
                          {(fixCount || fixMarks) && (
                            <span className="flex gap-2">
                              {fixCount && (
                                <button
                                  type="button"
                                  onClick={() => updateType(q.id, { count: fixCount })}
                                  className="rounded-md bg-white border border-amber-300 px-2 py-1 font-medium text-amber-900 hover:bg-amber-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
                                >
                                  Use {fixCount} questions
                                </button>
                              )}
                              {fixMarks && (
                                <button
                                  type="button"
                                  onClick={() => updateType(q.id, { marks: fixMarks })}
                                  className="rounded-md bg-white border border-amber-300 px-2 py-1 font-medium text-amber-900 hover:bg-amber-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
                                >
                                  Use {fixMarks} marks
                                </button>
                              )}
                            </span>
                          )}
                        </div>
                      )}
                      </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </fieldset>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
              <div>
                <span className="block text-xs font-semibold text-slate-700 mb-1.5">Total questions</span>
                <p className="px-3.5 py-2.5 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-900">{totals.count}</p>
              </div>
              <div>
                <span className="block text-xs font-semibold text-slate-700 mb-1.5">Total marks</span>
                <p className="px-3.5 py-2.5 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-900">{totals.marks}</p>
              </div>
              <div>
                <span className="block text-xs font-semibold text-slate-700 mb-1.5">Time limit (mins)</span>
                <p className="px-3.5 py-2.5 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-900">{totals.mins}</p>
              </div>
              <div>
                <label htmlFor="asm-versions" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Parallel versions
                </label>
                <input
                  id="asm-versions"
                  type="number"
                  min={1}
                  max={2}
                  value={numVersions}
                  onChange={(e) => setNumVersions(Math.min(2, Math.max(1, Number(e.target.value))))}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 shadow-xs"
                />
              </div>
            </div>

            {/* Emerald Callout matching Screen 2 in Figma */}
            <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200/90 text-emerald-800 text-xs flex items-center space-x-2 font-medium">
              <Check className="w-4 h-4 shrink-0" aria-hidden />
              <span>Multi-agent pipeline will execute: Blueprint → Item Generation → Adversarial Review → Moderation</span>
            </div>

            {/* Primary Action Button matching Screen 2 in Figma */}
            <div className="pt-2 space-y-2">
              <button
                type="submit"
                disabled={submitting || noModules || courseMissingOutcomes || hasUneven}
                aria-describedby="asm-submit-hint"
                className="w-full py-3 px-6 rounded-lg bg-emerald-700 hover:bg-emerald-800 active:bg-emerald-800 text-white font-semibold text-sm shadow-xs flex items-center justify-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-emerald-700 cursor-pointer"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
                    <span>Synthesizing assessment...</span>
                  </>
                ) : (
                  <span>Generate assessment</span>
                )}
              </button>
              <p id="asm-submit-hint" className={`text-center text-xs ${hasUneven ? "text-amber-800" : "text-slate-500"}`}>
                {hasUneven
                  ? "Fix the uneven marks highlighted above to generate."
                  : "Estimated generation time: 20-35 seconds"}
              </p>
            </div>
          </div>
        </form>

      </main>
    </div>
  );
}
