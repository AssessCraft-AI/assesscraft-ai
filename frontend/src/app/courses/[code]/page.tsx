"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiRequest } from "@/lib/api";
import { CourseDocuments, type DocumentItem } from "@/components/CourseDocuments";
import {
  BookOpen,
  Sparkles,
  FileText,
  CheckCircle2,
  Send,
  MessageSquare,
  AlertCircle,
  ExternalLink,
  Plus,
  Trash2,
  Layers,
  ChevronRight,
  ShieldCheck,
  RefreshCw,
  Table as TableIcon,
} from "lucide-react";

interface CLO {
  id: string;
  text: string;
  bloomLevel?: string;
}

interface Topic {
  id: string;
  name: string;
  cloIds: string[];
}

interface Course {
  id: string;
  code: string;
  title: string;
  ownerUid?: string;
  confirmed: boolean;
  clos: CLO[];
  topics: Topic[];
}


interface Citation {
  docId: string;
  title?: string;
  snippet: string;
  uri?: string;
}

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  citations?: Citation[];
  timestamp: string;
}


const BLOOM_LEVELS = ["remember", "understand", "apply", "analyse", "evaluate", "create"];

function CoursePageContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const { user, isLecturer } = useAuth();
  const courseCode = params.code as string;

  const [course, setCourse] = useState<Course | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingOutcomes, setSavingOutcomes] = useState(false);
  const [extracting, setExtracting] = useState(false);
  // Working copy of the CLOs while the lecturer edits them; null when not editing.
  const [draftClos, setDraftClos] = useState<CLO[] | null>(null);
  const [activeTab, setActiveTab] = useState<"matrix" | "outcomes" | "documents">("matrix");

  // Knowledge Assistant Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "msg-init",
      sender: "assistant",
      text: `Hello! I am your AssessCraft Knowledge Assistant for ${courseCode}. Ask me anything about syllabus coverage, past exam items, or QA manual repeat-paper policies.`,
      timestamp: "Just now",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [askingAssistant, setAskingAssistant] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);


  useEffect(() => {
    async function fetchCourseData() {
      try {
        setLoading(true);
        const [courseRes, docsRes] = await Promise.allSettled([
          apiRequest<Course>(`/courses/${courseCode}`),
          apiRequest<DocumentItem[]>(`/courses/${courseCode}/documents`),
        ]);

        if (courseRes.status === "fulfilled") {
          setCourse(courseRes.value);
          // New course with nothing extracted yet: start where the work is (uploading materials).
          if (!courseRes.value.clos.length) setActiveTab("documents");
        }
        if (docsRes.status === "fulfilled") {
          setDocuments(docsRes.value);
        }
      } catch (err) {
        console.error("Failed to load course details", err);
      } finally {
        setLoading(false);
      }
    }
    fetchCourseData();
  }, [courseCode]);

  useEffect(() => {
    if (searchParams.get("assistant") === "true") {
      setChatInput("Was a question on outer joins used in previous exams?");
    }
  }, [searchParams]);

  const handleAskAssistant = async (questionText?: string) => {
    const q = questionText || chatInput;
    if (!q.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: "user",
      text: q,
      timestamp: "Just now",
    };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setAskingAssistant(true);

    try {
      const res = await apiRequest<{ answer: string; citations: Citation[] }>(
        `/courses/${courseCode}/assistant`,
        {
          method: "POST",
          body: JSON.stringify({ question: q }),
        }
      );

      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: "assistant",
        text: res.answer,
        citations: res.citations,
        timestamp: "Just now",
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now() + 1}`,
          sender: "assistant",
          text: `Error reaching assistant: ${err.message}`,
          timestamp: "Just now",
        },
      ]);
    } finally {
      setAskingAssistant(false);
    }
  };

  // Generation needs real outcomes: without them the blueprint would invent CLOs.
  const hasOutcomes = !!course?.clos.length && !!course?.topics.length;
  const noOutcomesHint = "Upload course materials and extract outcomes first";

  const handleConfirmOutcomes = async () => {
    if (!course) return;
    setSavingOutcomes(true);
    try {
      const updated = await apiRequest<Course>(`/courses/${courseCode}/outcomes`, {
        method: "PUT",
        body: JSON.stringify({
          clos: course.clos,
          topics: course.topics,
          confirmed: true,
        }),
      });
      setCourse(updated);
    } catch (err: any) {
      alert(`Failed to save outcomes: ${err.message}`);
    } finally {
      setSavingOutcomes(false);
    }
  };

  const canEditOutcomes = isLecturer && !!user && course?.ownerUid === user.uid;
  // Only the module's lecturer writes its papers, and only once it has outcomes.
  const canCreate = hasOutcomes && canEditOutcomes;
  const createHint = canEditOutcomes ? noOutcomesHint : "Only the module's lecturer can create assessments";

  const updateDraftClo = (idx: number, patch: Partial<CLO>) =>
    setDraftClos((prev) => prev && prev.map((c, i) => (i === idx ? { ...c, ...patch } : c)));

  const addDraftClo = () =>
    setDraftClos((prev) => {
      if (!prev) return prev;
      const next = Math.max(0, ...prev.map((c) => parseInt(c.id.replace(/\D/g, ""), 10) || 0)) + 1;
      return [...prev, { id: `CLO${next}`, text: "", bloomLevel: "understand" }];
    });

  const handleSaveClos = async () => {
    if (!course || !draftClos) return;
    const clos = draftClos
      .map((c) => ({ ...c, text: c.text.trim() }))
      .filter((c) => c.text);
    const keptIds = new Set(clos.map((c) => c.id));
    setSavingOutcomes(true);
    try {
      const updated = await apiRequest<Course>(`/courses/${courseCode}/outcomes`, {
        method: "PUT",
        body: JSON.stringify({
          clos,
          // Topics must not point at outcomes that were just deleted.
          topics: course.topics.map((t) => ({ ...t, cloIds: t.cloIds.filter((id) => keptIds.has(id)) })),
          confirmed: course.confirmed,
        }),
      });
      setCourse(updated);
      setDraftClos(null);
    } catch (err: any) {
      alert(`Failed to save outcomes: ${err.message}`);
    } finally {
      setSavingOutcomes(false);
    }
  };

  const handleExtractOutcomes = async () => {
    if (
      course?.clos?.length &&
      !window.confirm("Re-extracting replaces the current learning outcomes and topics, including your edits. Continue?")
    ) {
      return;
    }
    setExtracting(true);
    try {
      await apiRequest(`/courses/${courseCode}/extract`, { method: "POST" });
      setCourse(await apiRequest<Course>(`/courses/${courseCode}`));
      setDraftClos(null);
      setActiveTab("outcomes");
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <div className="inline-block w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-500 mt-3">Loading course intelligence...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Course Header Banner matching Figma Screen 4 */}
      <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
              {course?.code}
            </span>
            {course?.confirmed && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>Outcomes Confirmed</span>
              </span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {course?.code} – Course overview
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {course?.title} · Course materials, outcomes &amp; topics
          </p>

          {/* 3 Status Badges matching Figma Screen 4 */}
          <div className="flex items-center gap-3 mt-3">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>{documents.length} Documents</span>
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>{course?.topics.length ?? 0} Topics</span>
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>{course?.clos.length ?? 0} LOs</span>
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {canCreate ? (
            <Link
              href={`/assessments/new?course=${course?.code}`}
              className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs transition-all shadow-xs"
            >
              <Sparkles className="w-4 h-4" />
              <span>+ New assessment</span>
            </Link>
          ) : (
            <span
              aria-disabled="true"
              title={createHint}
              className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg bg-emerald-700 text-white font-semibold text-xs shadow-xs opacity-50 cursor-not-allowed"
            >
              <Sparkles className="w-4 h-4" />
              <span>+ New assessment</span>
            </span>
          )}
          <button
            id="extract-outcomes-btn"
            onClick={handleExtractOutcomes}
            disabled={extracting || documents.length === 0}
            title={documents.length === 0 ? "Upload course materials first" : "Run DocIntel over all uploaded documents"}
            className="inline-flex items-center space-x-2 px-3.5 py-2.5 rounded-lg bg-white hover:bg-slate-50 disabled:opacity-50 text-slate-700 font-semibold text-xs transition-all border border-slate-200 shadow-xs cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>{extracting ? "Extracting… (up to a minute)" : course?.clos.length ? "Re-extract outcomes" : "Extract outcomes"}</span>
          </button>
          {!course?.confirmed && (
          <button
            id="confirm-outcomes-btn"
            onClick={handleConfirmOutcomes}
            disabled={savingOutcomes || !hasOutcomes}
            title={hasOutcomes ? undefined : "Extract outcomes before confirming them"}
            className="inline-flex items-center space-x-2 px-3.5 py-2.5 rounded-lg bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed text-slate-700 font-semibold text-xs transition-all border border-slate-200 shadow-xs cursor-pointer"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>{savingOutcomes ? "Saving..." : "Confirm Outcomes"}</span>
          </button>
          )}
        </div>
      </div>

      {/* Main Grid: Left is Matrix/Outcomes/Docs, Right is Quick Actions & Assistant */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Tabs */}
          <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
            <button
              onClick={() => setActiveTab("matrix")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 cursor-pointer ${
                activeTab === "matrix"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <TableIcon className="w-3.5 h-3.5 text-emerald-600" />
              <span>Blueprint Matrix</span>
            </button>
            <button
              id="tab-outcomes-btn"
              onClick={() => setActiveTab("outcomes")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 cursor-pointer ${
                activeTab === "outcomes"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <Layers className="w-3.5 h-3.5 text-emerald-600" />
              <span>CLOs &amp; Topics ({course?.clos.length || 0})</span>
            </button>
            <button
              id="tab-documents-btn"
              onClick={() => setActiveTab("documents")}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 cursor-pointer ${
                activeTab === "documents"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-emerald-600" />
              <span>Course Documents ({documents.length})</span>
            </button>
          </div>

          {/* TAB 1: BLUEPRINT MATRIX matching Screen 4 in Figma */}
          {activeTab === "matrix" && (
            <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Topic – Learning outcome coverage
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Extracted from your uploaded materials; per-assessment marks are set in each blueprint
                  </p>
                </div>
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {course?.topics.length ?? 0} topics
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-3.5 px-5">Topic</th>
                      <th className="py-3.5 px-4">Learning Outcomes</th>
                      <th className="py-3.5 px-5 text-right">Bloom Level</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {!course?.topics.length && (
                      <tr>
                        <td colSpan={3} className="py-6 px-5 text-center text-slate-500">
                          No topics yet. Upload your syllabus, notes and past papers, then click &quot;Extract outcomes&quot;.
                        </td>
                      </tr>
                    )}
                    {course?.topics.map((t) => (
                      <tr key={t.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3.5 px-5 font-semibold text-slate-900">{t.name}</td>
                        <td className="py-3.5 px-4 font-mono text-[11px] text-slate-600">{t.cloIds?.join(", ") || "—"}</td>
                        <td className="py-3.5 px-5 text-right">
                          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                            {course.clos.find((c) => t.cloIds?.includes(c.id))?.bloomLevel || "—"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: CLOs & Topics */}
          {activeTab === "outcomes" && (
            <div className="space-y-6">
              {/* CLOs List */}
              <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Course Learning Outcomes (CLOs)</span>
                  </h3>
                  {draftClos ? (
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setDraftClos(null)}
                        disabled={savingOutcomes}
                        className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs border border-slate-200 cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        id="save-clos-btn"
                        onClick={handleSaveClos}
                        disabled={savingOutcomes}
                        className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white font-semibold text-xs cursor-pointer"
                      >
                        {savingOutcomes ? "Saving..." : "Save outcomes"}
                      </button>
                    </div>
                  ) : canEditOutcomes ? (
                    <button
                      id="edit-clos-btn"
                      onClick={() => setDraftClos(course?.clos.map((c) => ({ ...c })) ?? [])}
                      className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs border border-slate-200 cursor-pointer"
                    >
                      Edit outcomes
                    </button>
                  ) : (
                    <span className="text-[11px] text-slate-500 font-medium">Bloom&apos;s Taxonomy Tagged</span>
                  )}
                </div>

                {draftClos && (
                  <div className="space-y-2.5">
                    {draftClos.map((clo, idx) => (
                      <div
                        key={clo.id}
                        className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-start space-x-3"
                      >
                        <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0 mt-0.5 font-mono">
                          {clo.id}
                        </span>
                        <div className="flex-1 space-y-1.5">
                          <textarea
                            aria-label={`${clo.id} text`}
                            value={clo.text}
                            onChange={(e) => updateDraftClo(idx, { text: e.target.value })}
                            rows={2}
                            placeholder="Students will be able to..."
                            className="w-full bg-white border border-slate-200 text-slate-900 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-600"
                          />
                          <select
                            aria-label={`${clo.id} Bloom level`}
                            value={clo.bloomLevel || "understand"}
                            onChange={(e) => updateDraftClo(idx, { bloomLevel: e.target.value })}
                            className="bg-white border border-slate-200 text-slate-700 text-[11px] rounded px-2 py-1 focus:outline-none focus:border-emerald-600"
                          >
                            {BLOOM_LEVELS.map((b) => (
                              <option key={b} value={b}>
                                Bloom: {b}
                              </option>
                            ))}
                          </select>
                        </div>
                        <button
                          aria-label={`Delete ${clo.id}`}
                          onClick={() => setDraftClos((prev) => prev && prev.filter((_, i) => i !== idx))}
                          className="p-1.5 rounded text-slate-500 hover:text-red-600 hover:bg-red-50 cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={addDraftClo}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs border border-dashed border-slate-300 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add outcome</span>
                    </button>
                    <p className="text-[11px] text-slate-500">Empty outcomes are dropped on save. Deleting one also removes it from its topics.</p>
                  </div>
                )}

                <div className={draftClos ? "hidden" : "space-y-2.5"}>
                  {course?.clos.map((clo) => (
                    <div
                      key={clo.id}
                      className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-start space-x-3"
                    >
                      <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0 mt-0.5 font-mono">
                        {clo.id}
                      </span>
                      <div className="flex-1">
                        <p className="text-xs text-slate-800 leading-relaxed font-medium">{clo.text}</p>
                        <div className="mt-1.5 flex items-center space-x-2">
                          <span className="text-[11px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded bg-slate-200/70 text-slate-700">
                            Bloom: {clo.bloomLevel || "understand"}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Topics List */}
              <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                    <BookOpen className="w-4 h-4 text-emerald-600" />
                    <span>Syllabus Topics &amp; CLO Mapping</span>
                  </h3>
                  <span className="text-[11px] text-slate-500">Curricular Entities</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {course?.topics.map((t) => (
                    <div
                      key={t.id}
                      className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5"
                    >
                      <div className="text-xs font-semibold text-slate-900">{t.name}</div>
                      <div className="flex flex-wrap gap-1">
                        {t.cloIds?.map((cid) => (
                          <span
                            key={cid}
                            className="text-[11px] font-medium font-mono px-1.5 py-0.5 rounded bg-white text-slate-700 border border-slate-200"
                          >
                            {cid}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Course Documents */}
          {activeTab === "documents" && (
            <CourseDocuments
              courseCode={courseCode}
              documents={documents}
              onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])}
            />
          )}
        </div>

        {/* Right Column: Quick Assessment & Assistant (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          {/* Knowledge Assistant Chat Side Panel */}
          <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs flex flex-col h-[520px]">
            {/* Header */}
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Knowledge Assistant</h3>
                  <p className="text-[11px] text-slate-500">Vertex AI Search · Grounded in {course?.code} Docs</p>
                </div>
              </div>
            </div>

            {/* Quick Demo Prompts */}
            <div className="px-3 py-2 bg-slate-50 border-b border-slate-100 flex items-center space-x-1.5 overflow-x-auto text-[11px]">
              <span className="text-slate-500 text-[11px] shrink-0 font-medium">Try:</span>
              <button
                id="quick-query-outer-joins"
                onClick={() => handleAskAssistant("Which topics appear most often in the past papers?")}
                className="px-2 py-0.5 rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 whitespace-nowrap text-[11px] transition-colors cursor-pointer"
              >
                Most-examined topics?
              </button>
              <button
                id="quick-query-repeat-papers"
                onClick={() => handleAskAssistant("Summarise the course learning outcomes.")}
                className="px-2 py-0.5 rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 whitespace-nowrap text-[11px] transition-colors cursor-pointer"
              >
                Summarise the CLOs
              </button>
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/40">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[90%] p-3 rounded-xl text-xs leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-emerald-700 text-white rounded-br-none shadow-xs"
                        : "bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-xs"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>

                    {/* Citations Chips */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-slate-100 space-y-1">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 flex items-center space-x-1">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Grounded Source Citations</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {msg.citations.map((cite, cIdx) => (
                            <button
                              key={cIdx}
                              onClick={() => setSelectedCitation(cite)}
                              className="text-[11px] px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 flex items-center space-x-1 transition-colors cursor-pointer"
                            >
                              <span>{cite.title || `Source [${cIdx + 1}]`}</span>
                              <ExternalLink className="w-2.5 h-2.5 text-slate-500" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
                </div>
              ))}

              {askingAssistant && (
                <div className="flex items-center space-x-2 text-xs text-slate-500 p-2">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                  <span>Searching course archives with Vertex AI Search...</span>
                </div>
              )}
            </div>

            {/* Citation Preview Drawer */}
            {selectedCitation && (
              <div className="p-3 bg-white border-t border-slate-200 text-xs space-y-1">
                <div className="flex items-center justify-between text-emerald-700 font-semibold">
                  <span>Cited Source: {selectedCitation.title}</span>
                  <button
                    onClick={() => setSelectedCitation(null)}
                    className="text-slate-500 hover:text-slate-700 text-[11px] cursor-pointer"
                  >
                    Close
                  </button>
                </div>
                <p className="text-slate-700 text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-200 italic">
                  &ldquo;{selectedCitation.snippet}&rdquo;
                </p>
              </div>
            )}

            {/* Chat Input */}
            <div className="p-3 border-t border-slate-100 bg-white">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleAskAssistant();
                }}
                className="flex items-center space-x-2"
              >
                <input
                  id="assistant-chat-input"
                  aria-label="Ask the knowledge assistant"
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about syllabus topics, past exams..."
                  className="flex-1 bg-white border border-slate-200 text-slate-900 placeholder-slate-400 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-600 shadow-xs"
                />
                <button
                  id="assistant-chat-send-btn"
                  aria-label="Send question"
                  type="submit"
                  disabled={!chatInput.trim() || askingAssistant}
                  className="p-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white transition-colors cursor-pointer shadow-xs"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CoursePage() {
  return (
    <React.Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 py-16 text-center">
          <div className="inline-block w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 mt-3">Loading course intelligence...</p>
        </div>
      }
    >
      <CoursePageContent />
    </React.Suspense>
  );
}
