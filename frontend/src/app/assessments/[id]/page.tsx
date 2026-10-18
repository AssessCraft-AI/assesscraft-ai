"use client";

import React, { useState, useEffect, useCallback, Suspense, useMemo, useRef } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import AgentTraceDrawer from "@/components/AgentTraceDrawer";
import {
  StageNav,
  NextActionStrip,
  NoticeToast,
  ConfirmDialog,
  WORKFLOW_TABS,
  type WorkflowTab,
  type StageDef,
  type NextAction,
  type Notice,
} from "@/components/AssessmentWorkflow";
import { apiRequest, apiDownload } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import {
  AlertTriangle,
  BarChart3,
  Bot,
  Brain,
  Check,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Copy,
  Download,
  Eye,
  FileText,
  Flag,
  GraduationCap,
  Info,
  Send,
  Landmark,
  Layers,
  Lightbulb,
  ListChecks,
  Loader2,
  MessageSquare,
  PenLine,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Target,
  Timer,
  Zap,
  Keyboard,
  X,
} from "lucide-react";

interface BlueprintCell {
  cloId: string;
  topicId: string;
  bloom: string;
  qType: string;
  count: number;
  marksEach: number;
}

interface Blueprint {
  assessmentId: string;
  cells: BlueprintCell[];
  totals: {
    totalMarks: number;
    totalItems: number;
    targetMarks: number;
    bloomDistribution?: Record<string, number>;
    typeDistribution?: Record<string, number>;
  };
  valid: boolean;
  violations: string[];
  rationale?: string;
}

interface Option {
  id: string;
  text: string;
}

interface SourceCitation {
  docId: string;
  title?: string;
  snippet: string;
  uri?: string;
}

interface Item {
  id: string;
  assessmentId: string;
  stem: string;
  options?: Option[];
  key: string;
  rationale: string;
  qType: string;
  marks: number;
  cloId: string;
  topicId: string;
  bloom: string;
  difficulty: number;
  sourceCitations: SourceCitation[];
  status: "candidate" | "accepted" | "rejected";
}

interface Flag {
  id: string;
  itemId: string;
  assessmentId: string;
  type: string;
  severity: "high" | "medium" | "low";
  detail: string;
  evidence: string;
  resolution?: "accepted" | "dismissed" | "edited";
  resolvedBy?: string;
  createdAt?: string;
}

interface PaperVersion {
  id: string;
  assessmentId: string;
  label: string;
  itemIds: string[];
  solverStats?: {
    status?: string;
    mode?: string;
    durationMs?: number;
    branches?: number;
    wallTime?: number;
  };
}

interface EquivalenceReport {
  assessmentId: string;
  perVersion: Record<string, any>;
  deviations: Record<string, any>;
  guaranteed: string[];
  estimated: string[];
  limitations: string[];
  solverStatus: string;
}

interface ModerationCheckItem {
  id: string;
  title: string;
  passed: boolean;
  notes?: string;
}

interface ModerationComment {
  id: string;
  author: string;
  role: string;
  text: string;
  citedItemIds?: string[];
  createdAt?: string;
}

interface ModerationRecord {
  assessmentId: string;
  checklist: ModerationCheckItem[];
  aiComments: ModerationComment[];
  humanComments: ModerationComment[];
  executiveSummary?: string;
  decision?: "approved" | "changes_requested" | null;
  decidedBy?: string;
  decidedAt?: string;
  updatedAt?: string;
  generatedBy?: "agent" | "fallback";
  stale?: boolean;
}

interface Assessment {
  id: string;
  courseId: string;
  title: string;
  request: string;
  totalMarks: number;
  durationMins: number;
  numVersions: number;
  status: string;
  runId?: string;
  createdBy?: string | null;
  createdByUid?: string | null;
  moderatorUid?: string | null;
  submittedAt?: string | null;
}

interface ContactSummary {
  uid: string;
  email: string;
  displayName: string;
  role: string;
  institution?: string | null;
}

/** The paper's module with its owner and moderator; moderation is assigned per module. */
interface ModuleContacts {
  courseId: string;
  code: string;
  title: string;
  owner?: ContactSummary | null;
  moderator?: ContactSummary | null;
}

const SUBMITTABLE_STATUSES = ["assembled", "changes_requested"];

const QTYPE_LABEL: Record<string, string> = { mcq: "MCQ", short_answer: "Structured", essay: "Free response" };
const QTYPE_ORDER = ["mcq", "short_answer", "essay"];
const fmtTypeBreakdown = (b?: Record<string, number>) =>
  Object.entries(b || {}).map(([k, n]) => `${n} ${QTYPE_LABEL[k] ?? k}`).join(" / ") || "—";

function AssessmentWorkspaceContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const assessmentId = params?.id as string;
  const { user, role, isModerator } = useAuth();

  const tabParam = searchParams.get("tab") as WorkflowTab | null;
  const [activeTab, setActiveTab] = useState<WorkflowTab>(
    tabParam && WORKFLOW_TABS.includes(tabParam) ? tabParam : "blueprint"
  );
  const goTab = useCallback((tab: WorkflowTab) => {
    setActiveTab(tab);
    const sp = new URLSearchParams(window.location.search);
    sp.set("tab", tab);
    window.history.replaceState(null, "", `?${sp.toString()}`);
  }, []);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [flags, setFlags] = useState<Flag[]>([]);
  const [versions, setVersions] = useState<PaperVersion[]>([]);
  const [equivalenceReport, setEquivalenceReport] = useState<EquivalenceReport | null>(null);
  const [moderationRecord, setModerationRecord] = useState<ModerationRecord | null>(null);
  const [contacts, setContacts] = useState<ModuleContacts | null>(null);
  const [submittingForModeration, setSubmittingForModeration] = useState(false);
  const [activeVersionLabel, setActiveVersionLabel] = useState<string>("A");
  const [versionItems, setVersionItems] = useState<Record<string, Item[]>>({});

  // Moderation state
  const [humanCommentText, setHumanCommentText] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [postingComment, setPostingComment] = useState(false);
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [generatingModeration, setGeneratingModeration] = useState(false);

  // Export state
  const [exportVersion, setExportVersion] = useState<string>("A");
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [examPaperPreviewOpen, setExamPaperPreviewOpen] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadWarnings, setLoadWarnings] = useState<string[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [confirmApproveOpen, setConfirmApproveOpen] = useState(false);
  const [expandedFlagItems, setExpandedFlagItems] = useState<Record<string, boolean>>({});
  const [selectedFlagItems, setSelectedFlagItems] = useState<Record<string, boolean>>({});

  const notify = useCallback((kind: Notice["kind"], text: string, undo?: () => void) => {
    setNotice({ id: Date.now(), kind, text, undo });
  }, []);
  useEffect(() => {
    if (!notice || notice.kind === "error") return;
    const t = setTimeout(() => setNotice(null), notice.undo ? 6500 : 4500);
    return () => clearTimeout(t);
  }, [notice]);

  // Agent Trace drawer state
  const [isTraceOpen, setIsTraceOpen] = useState(searchParams.get("trace") === "open");
  const [showShortcuts, setShowShortcuts] = useState(false);

  // Global keyboard shortcuts: [ / ] cycle workflow tabs, Alt+1..6 direct jump, Esc closes modals
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        if (e.key === "Escape") target.blur();
        return;
      }

      if (e.key === "Escape") {
        if (confirmApproveOpen) { setConfirmApproveOpen(false); return; }
        if (examPaperPreviewOpen) { setExamPaperPreviewOpen(false); return; }
        if (isTraceOpen) { setIsTraceOpen(false); return; }
        if (showShortcuts) { setShowShortcuts(false); return; }
      }

      if (e.key === "?" || (e.shiftKey && e.key === "/")) {
        setShowShortcuts((prev) => !prev);
        return;
      }

      // Toggle Agent Trace drawer: t or Alt+t
      if ((e.key === "t" || e.key === "T") && (e.altKey || !target)) {
        e.preventDefault();
        setIsTraceOpen((prev) => !prev);
        return;
      }

      // Toggle Exam paper preview: p or Alt+p
      if ((e.key === "p" || e.key === "P") && (e.altKey || !target)) {
        if (activeTab === "export" || activeTab === "solver") {
          e.preventDefault();
          setExamPaperPreviewOpen((prev) => !prev);
          return;
        }
      }

      const tabs: WorkflowTab[] = ["blueprint", "pool", "review", "solver", "moderation", "export"];
      if (e.key === "[" || e.key === "{") {
        e.preventDefault();
        const idx = tabs.indexOf(activeTab);
        if (idx > 0) goTab(tabs[idx - 1]);
      } else if (e.key === "]" || e.key === "}") {
        e.preventDefault();
        const idx = tabs.indexOf(activeTab);
        if (idx < tabs.length - 1) goTab(tabs[idx + 1]);
      } else if (e.altKey && !isNaN(Number(e.key))) {
        const num = Number(e.key);
        if (num >= 1 && num <= tabs.length) {
          e.preventDefault();
          goTab(tabs[num - 1]);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeTab, confirmApproveOpen, examPaperPreviewOpen, isTraceOpen, showShortcuts, goTab]);

  // Filter state for Item Pool
  const [filterType, setFilterType] = useState<string>("all");
  const [filterBloom, setFilterBloom] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedRationales, setExpandedRationales] = useState<Record<string, boolean>>({});

  // Filter state for Reviewer Flags
  const [flagFilterType, setFlagFilterType] = useState<string>("all");
  const [flagFilterSeverity, setFlagFilterSeverity] = useState<string>("all");
  const [flagFilterStatus, setFlagFilterStatus] = useState<string>("all");

  // Solver Paper Section toggle
  const [solverSectionFilter, setSolverSectionFilter] = useState<string>("all");
  const [showAnswerKeys, setShowAnswerKeys] = useState(false);

  // Action loading states
  const [generatingBp, setGeneratingBp] = useState(false);
  const [generatingPool, setGeneratingPool] = useState(false);
  const [savingBp, setSavingBp] = useState(false);
  // Matrix edits not yet saved; drafting the pool must not run against the stale server copy.
  const [bpDirty, setBpDirty] = useState(false);
  const [runningReviewer, setRunningReviewer] = useState(false);
  const [runningSolver, setRunningSolver] = useState(false);

  const versionColors: Record<string, string> = {
    A: "#0284c7", // sky-600
    B: "#475569", // slate-600
    C: "#7dd3fc", // sky-300
    D: "#94a3b8", // slate-400
  };

  const { cloChartData, bloomChartData, versionLabels } = useMemo(() => {
    if (!equivalenceReport || !equivalenceReport.perVersion) {
      return { cloChartData: [], bloomChartData: [], versionLabels: [] };
    }

    const labels = Object.keys(equivalenceReport.perVersion).sort();
    if (labels.length === 0) {
      return { cloChartData: [], bloomChartData: [], versionLabels: [] };
    }

    // 1. Gather all unique CLO IDs
    const cloSet = new Set<string>();
    labels.forEach((vLabel) => {
      const vData = equivalenceReport.perVersion[vLabel];
      if (vData?.cloBreakdown) {
        Object.keys(vData.cloBreakdown).forEach((k) => cloSet.add(k));
      }
    });

    // Fallback: If cloBreakdown wasn't populated in report, compute from items
    if (cloSet.size === 0 && versions.length > 0) {
      versions.forEach((ver) => {
        const verItems = items.filter((it) => ver.itemIds?.includes(it.id));
        verItems.forEach((it) => {
          if (it.cloId) cloSet.add(it.cloId);
        });
      });
    }

    const sortedClos = Array.from(cloSet).sort();
    const cloData = sortedClos.map((cloId) => {
      const row: Record<string, any> = { clo: cloId };
      labels.forEach((vLabel) => {
        const vData = equivalenceReport.perVersion[vLabel];
        if (vData?.cloBreakdown && vData.cloBreakdown[cloId] !== undefined) {
          row[`Version ${vLabel}`] = vData.cloBreakdown[cloId];
        } else {
          const ver = versions.find((v) => v.label === vLabel);
          const verItems = items.filter((it) => ver?.itemIds?.includes(it.id) && it.cloId === cloId);
          row[`Version ${vLabel}`] = verItems.reduce((acc, it) => acc + (it.marks || 0), 0);
        }
      });
      return row;
    });

    // 2. Gather Bloom levels
    const standardBloom = ["remember", "understand", "apply", "analyse", "analyze", "evaluate", "create"];
    const bloomSet = new Set<string>();
    labels.forEach((vLabel) => {
      const vData = equivalenceReport.perVersion[vLabel];
      if (vData?.bloomBreakdown) {
        Object.keys(vData.bloomBreakdown).forEach((k) => bloomSet.add(k.toLowerCase()));
      }
    });

    if (bloomSet.size === 0 && versions.length > 0) {
      versions.forEach((ver) => {
        const verItems = items.filter((it) => ver.itemIds?.includes(it.id));
        verItems.forEach((it) => {
          if (it.bloom) bloomSet.add(it.bloom.toLowerCase());
        });
      });
    }

    const sortedBloom = standardBloom.filter((b) => bloomSet.has(b));
    bloomSet.forEach((b) => {
      if (!sortedBloom.includes(b)) sortedBloom.push(b);
    });

    const bloomData = sortedBloom.map((b) => {
      const capitalized = b.charAt(0).toUpperCase() + b.slice(1);
      const row: Record<string, any> = { bloom: capitalized };
      labels.forEach((vLabel) => {
        const vData = equivalenceReport.perVersion[vLabel];
        if (vData?.bloomBreakdown && vData.bloomBreakdown[b] !== undefined) {
          row[`Version ${vLabel}`] = vData.bloomBreakdown[b];
        } else {
          const ver = versions.find((v) => v.label === vLabel);
          const verItems = items.filter(
            (it) => ver?.itemIds?.includes(it.id) && it.bloom?.toLowerCase() === b.toLowerCase()
          );
          row[`Version ${vLabel}`] = verItems.reduce((acc, it) => acc + (it.marks || 0), 0);
        }
      });
      return row;
    });

    return { cloChartData: cloData, bloomChartData: bloomData, versionLabels: labels };
  }, [equivalenceReport, versions, items]);

  const loadData = useCallback(async () => {
    if (!assessmentId) return;
    try {
      setLoading(true);
      const warnings: string[] = [];
      const soft = <T,>(req: Promise<T>, what: string, fallback: T, missingIsFine = false) =>
        req.catch((e: Error) => {
          if (!(missingIsFine && e.message.includes("(404)"))) warnings.push(what);
          return fallback;
        });
      const [asmData, bpData, itemsData, flagsData, versionsData, eqData, modData] = await Promise.all([
        apiRequest<Assessment>(`/assessments/${assessmentId}`),
        apiRequest<Blueprint>(`/assessments/${assessmentId}/blueprint`),
        apiRequest<Item[]>(`/assessments/${assessmentId}/items`),
        apiRequest<Flag[]>(`/assessments/${assessmentId}/flags`),
        soft(apiRequest<PaperVersion[]>(`/assessments/${assessmentId}/versions`), "paper versions", [] as PaperVersion[]),
        soft(apiRequest<EquivalenceReport>(`/assessments/${assessmentId}/equivalence`), "equivalence report", null),
        soft(apiRequest<ModerationRecord>(`/assessments/${assessmentId}/moderation`), "moderation pack", null, true),
      ]);
      setAssessment(asmData);
      setBlueprint(bpData);
      setBpDirty(false);
      setItems(itemsData || []);
      setFlags(flagsData || []);
      setVersions(versionsData || []);
      setEquivalenceReport(eqData);
      setModerationRecord(modData);
      setLoadWarnings(warnings);
      setError(null);
    } catch (err: any) {
      console.error("Failed to load assessment data:", err);
      setError(err.message || "Could not load assessment details");
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // The moderator comes from the paper's module, not from the lecturer.
  const courseId = assessment?.courseId;
  useEffect(() => {
    if (!courseId) return;
    apiRequest<ModuleContacts>(`/courses/${encodeURIComponent(courseId)}/contacts`)
      .then(setContacts)
      .catch(() => setContacts({ courseId, code: courseId, title: "", moderator: null }));
  }, [courseId, role]);

  // Fetch Version Items when activeVersionLabel changes
  const fetchVersionItems = useCallback(
    async (verId: string, label: string) => {
      try {
        const itList = await apiRequest<Item[]>(`/assessments/${assessmentId}/versions/${verId}/items`);
        setVersionItems((prev) => ({ ...prev, [label]: itList }));
      } catch (e) {
        console.warn("Could not load version items:", e);
      }
    },
    [assessmentId]
  );

  useEffect(() => {
    if (versions && versions.length > 0) {
      const currentVer = versions.find((v) => v.label === activeVersionLabel) || versions[0];
      if (currentVer && !versionItems[currentVer.label]) {
        fetchVersionItems(currentVer.id, currentVer.label);
      }
    }
  }, [versions, activeVersionLabel, versionItems, fetchVersionItems]);

  // Handle cell edit
  const handleCellChange = (index: number, field: "count" | "marksEach", value: number) => {
    if (!blueprint) return;
    const newCells = [...blueprint.cells];
    newCells[index] = {
      ...newCells[index],
      [field]: Math.max(0, value),
    };

    const totalMarks = newCells.reduce((sum, c) => sum + c.count * c.marksEach, 0);
    const totalItems = newCells.reduce((sum, c) => sum + c.count, 0);
    const target = assessment?.totalMarks || 100;
    const isValid = totalMarks === target;

    setBlueprint({
      ...blueprint,
      cells: newCells,
      totals: {
        ...blueprint.totals,
        totalMarks,
        totalItems,
        targetMarks: target,
      },
      valid: isValid,
      violations: isValid ? [] : [`Total marks (${totalMarks}) do not match target (${target})`],
    });
    setBpDirty(true);
  };

  const handleSaveBlueprint = async (): Promise<boolean> => {
    if (!blueprint) return false;
    try {
      setSavingBp(true);
      const updated = await apiRequest<Blueprint>(`/assessments/${assessmentId}/blueprint`, {
        method: "PUT",
        body: JSON.stringify(blueprint),
      });
      setBlueprint(updated);
      setBpDirty(false);
      await loadData();
      return true;
    } catch (err: any) {
      notify("error", `Error saving blueprint: ${err.message}`);
      return false;
    } finally {
      setSavingBp(false);
    }
  };

  const handleRegenerateBlueprint = async () => {
    if (bpDirty && !window.confirm("Regenerating replaces your unsaved matrix edits. Continue?")) return;
    try {
      setGeneratingBp(true);
      setIsTraceOpen(true);
      await apiRequest(`/assessments/${assessmentId}/blueprint`, { method: "POST" });
      setTimeout(async () => {
        await loadData();
        setGeneratingBp(false);
      }, 2500);
    } catch (err: any) {
      notify("error", `Blueprint generation failed: ${err.message}`);
      setGeneratingBp(false);
    }
  };

  const handleGeneratePool = async () => {
    if (bpDirty && !(await handleSaveBlueprint())) return;
    try {
      setGeneratingPool(true);
      setIsTraceOpen(true);
      await apiRequest(`/assessments/${assessmentId}/pool`, { method: "POST" });
      setTimeout(async () => {
        await loadData();
        setGeneratingPool(false);
        goTab("pool");
      }, 3000);
    } catch (err: any) {
      notify("error", `Pool generation failed: ${err.message}`);
      setGeneratingPool(false);
    }
  };

  const handleRunReviewer = async () => {
    try {
      setRunningReviewer(true);
      setIsTraceOpen(true);
      await apiRequest(`/assessments/${assessmentId}/review`, { method: "POST" });
      setTimeout(async () => {
        await loadData();
        setRunningReviewer(false);
        goTab("review");
      }, 3000);
    } catch (err: any) {
      notify("error", `Reviewer audit failed: ${err.message}`);
      setRunningReviewer(false);
    }
  };

  const handleRunSolver = async () => {
    try {
      setRunningSolver(true);
      setIsTraceOpen(true);
      await apiRequest(`/assessments/${assessmentId}/assemble`, { method: "POST" });
      setTimeout(async () => {
        await loadData();
        setRunningSolver(false);
        goTab("solver");
      }, 2500);
    } catch (err: any) {
      notify("error", `CP-SAT assembly failed: ${err.message}`);
      setRunningSolver(false);
    }
  };

  const handleGenerateModeration = async () => {
    try {
      setGeneratingModeration(true);
      setIsTraceOpen(true);
      const res = await apiRequest<ModerationRecord>(`/assessments/${assessmentId}/moderation`, { method: "POST" });
      setModerationRecord(res);
      await loadData();
    } catch (err: any) {
      notify("error", `Moderation audit failed: ${err.message}`);
    } finally {
      setGeneratingModeration(false);
    }
  };

  const handleAddComment = async () => {
    if (!humanCommentText.trim()) return;
    try {
      setPostingComment(true);
      const updated = await apiRequest<ModerationRecord>(`/assessments/${assessmentId}/comments`, {
        method: "POST",
        body: JSON.stringify({ text: humanCommentText }),
      });
      setModerationRecord(updated);
      setHumanCommentText("");
    } catch (err: any) {
      notify("error", `Failed to add comment: ${err.message}`);
    } finally {
      setPostingComment(false);
    }
  };

  const handleSubmitForModeration = async () => {
    try {
      setSubmittingForModeration(true);
      await apiRequest<Assessment>(`/assessments/${assessmentId}/submit`, { method: "POST" });
      await loadData();
      notify(
        "success",
        `Submitted. ${contacts?.moderator?.displayName || "The module's moderator"} has been notified and the AI moderation pack is being prepared.`
      );
    } catch (err: any) {
      notify("error", `Couldn't submit for moderation: ${String(err.message).replace(/^API Error \(\d+\): /, "")}`);
    } finally {
      setSubmittingForModeration(false);
    }
  };

  const handleSubmitDecision = async (decision: "approved" | "changes_requested") => {
    try {
      setSubmittingDecision(true);
      const updated = await apiRequest<ModerationRecord>(`/assessments/${assessmentId}/decision`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          comment: decisionNote.trim() || undefined,
        }),
      });
      setModerationRecord(updated);
      setDecisionNote("");
      await loadData();
      notify(
        "success",
        decision === "approved"
          ? "Approved. The package is locked and ready to export."
          : "Changes requested. The lecturer will see your notes."
      );
    } catch (err: any) {
      notify("error", `Moderation decision failed: ${err.message}`);
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleDownloadExport = async (format: "pdf" | "keys" | "moodle_xml" | "clo_csv") => {
    try {
      setDownloadingFormat(format);
      const ext = format === "pdf" || format === "keys" ? "pdf" : format === "moodle_xml" ? "xml" : "csv";
      const filename = `${assessmentId}_Version_${exportVersion}_${format}.${ext}`;
      await apiDownload(`/assessments/${assessmentId}/export?format=${format}&version=${exportVersion}`, filename);
    } catch (err: any) {
      notify("error", `Export download failed: ${err.message}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Resolutions commit after a short undo window; a newer action commits the pending one first.
  const pendingCommit = useRef<{ timer: ReturnType<typeof setTimeout>; run: () => Promise<void> } | null>(null);
  const flushPending = async () => {
    const p = pendingCommit.current;
    if (!p) return;
    clearTimeout(p.timer);
    pendingCommit.current = null;
    await p.run();
  };
  useEffect(
    () => () => {
      const p = pendingCommit.current;
      if (p) {
        clearTimeout(p.timer);
        p.run();
      }
    },
    []
  );

  const resolveFlags = async (
    flagIds: string[],
    resolution: "accepted" | "dismissed",
    detail: string,
    label: string
  ) => {
    if (flagIds.length === 0) return;
    await flushPending();
    const snapshot = flags;
    setFlags((prev) => prev.map((f) => (flagIds.includes(f.id) ? { ...f, resolution, resolvedBy: user.email } : f)));
    setSelectedFlagItems({});
    const run = async () => {
      try {
        for (const id of flagIds) {
          await apiRequest<Flag>(`/flags/${id}`, { method: "PATCH", body: JSON.stringify({ resolution, detail }) });
        }
      } catch (err: any) {
        notify("error", `Couldn't save that decision: ${err.message}`);
      }
      await loadData();
    };
    const timer = setTimeout(() => {
      pendingCommit.current = null;
      run();
    }, 6000);
    pendingCommit.current = { timer, run };
    notify("success", label, () => {
      clearTimeout(timer);
      pendingCommit.current = null;
      setFlags(snapshot);
      setNotice(null);
    });
  };

  const handleUpdateItemStatus = async (itemId: string, newStatus: "accepted" | "rejected" | "candidate") => {
    try {
      const updated = await apiRequest<Item>(`/items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      setItems((prev) => prev.map((item) => (item.id === itemId ? updated : item)));
    } catch (err: any) {
      notify("error", `Failed to update item: ${err.message}`);
    }
  };

  const handleAcceptAll = async (ids: string[]) => {
    await Promise.all(ids.map((id) => handleUpdateItemStatus(id, "accepted")));
    notify("success", `Accepted ${ids.length} questions.`);
  };

  const toggleRationale = (itemId: string) => {
    setExpandedRationales((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }));
  };

  const filteredItems = items.filter((item) => {
    if (filterType !== "all" && item.qType !== filterType) return false;
    if (filterBloom !== "all" && item.bloom !== filterBloom) return false;
    if (filterStatus !== "all" && item.status !== filterStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const inStem = item.stem.toLowerCase().includes(q);
      const inOptions = item.options?.some((o) => o.text.toLowerCase().includes(q));
      if (!inStem && !inOptions) return false;
    }
    return true;
  });

  const filteredFlags = flags.filter((flag) => {
    if (flagFilterType !== "all" && flag.type !== flagFilterType) return false;
    if (flagFilterSeverity !== "all" && flag.severity !== flagFilterSeverity) return false;
    if (flagFilterStatus === "unresolved" && flag.resolution) return false;
    if (flagFilterStatus === "resolved" && !flag.resolution) return false;
    return true;
  });

  // Bloom level is a category, not a status, so it stays neutral.
  const getBloomBadgeColor = (_bloom: string) => "bg-slate-50 text-slate-700 border-slate-200";

  const getFlagBadge = (type: string) => {
    switch (type) {
      case "key_mismatch":
        return { label: "Key Mismatch", Icon: Zap, color: "bg-rose-50 text-rose-700 border-rose-200" };
      case "duplicate_past":
        return { label: "Past Exam Duplicate", Icon: FileText, color: "bg-amber-50 text-amber-700 border-amber-200" };
      case "duplicate_pool":
        return { label: "Pool Duplicate", Icon: Copy, color: "bg-amber-50 text-amber-700 border-amber-200" };
      case "item_flaw":
        return { label: "Psychometric Flaw", Icon: AlertTriangle, color: "bg-amber-50 text-amber-700 border-amber-200" };
      case "misaligned_clo":
        return { label: "Misaligned CLO", Icon: Target, color: "bg-amber-50 text-amber-700 border-amber-200" };
      case "ambiguous":
        return { label: "Ambiguous Stem", Icon: AlertTriangle, color: "bg-amber-50 text-amber-700 border-amber-200" };
      case "bloom_doubt":
        return { label: "Bloom Level Doubt", Icon: Brain, color: "bg-sky-50 text-sky-700 border-sky-200" };
      default:
        return { label: "Quality Flag", Icon: Flag, color: "bg-slate-100 text-slate-700 border-slate-200" };
    }
  };

  if (loading && !assessment) {
    return (
      <div className="min-h-full py-24 flex items-center justify-center bg-slate-50 text-slate-900">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-700">Loading Assessment Workspace...</p>
        </div>
      </div>
    );
  }

  const currentMarks = blueprint?.totals?.totalMarks || 0;
  const targetMarks = assessment?.totalMarks || 100;
  const isMarksValid = currentMarks === targetMarks;
  const requiredItemCount = blueprint?.totals?.totalItems || 0;
  // Mirrors the item writer: one set per version (versions share no items) plus a 0.5x spare.
  const poolMultiplier = (assessment?.numVersions || 2) + 0.5;
  const poolTarget = Math.ceil(requiredItemCount * poolMultiplier);
  const poolItemCount = items.length;
  const bufferMultiplier = requiredItemCount > 0 ? (poolItemCount / requiredItemCount).toFixed(1) : "0";

  const keyMismatchCount = flags.filter((f) => f.type === "key_mismatch").length;
  const pastDuplicateCount = flags.filter((f) => f.type === "duplicate_past").length;
  const poolDuplicateCount = flags.filter((f) => f.type === "duplicate_pool").length;
  const flawCount = flags.filter((f) => f.type === "item_flaw").length;
  const flaggedItemIds = new Set(flags.map((f) => f.itemId));
  const cleanItemsCount = Math.max(0, items.length - flaggedItemIds.size);

  // Readiness is derived from the data, never asserted.
  const unresolvedFlags = flags.filter((f) => !f.resolution);
  const reviewRun =
    flags.length > 0 ||
    ["reviewed", "assembled", "in_moderation", "approved", "changes_requested"].includes(assessment?.status || "");
  const expectedVersions = assessment?.numVersions || 2;
  const versionsAssembled = versions.length >= expectedVersions;
  // Mirrors the backend's LOCKED_STATUSES: content is frozen in moderation and after sign-off.
  const isLocked = ["in_moderation", "approved"].includes(assessment?.status || "");
  const lockedTitle = isLocked ? "Locked while the paper is in moderation or approved" : undefined;
  const sharedItemCount =
    versions.length > 1
      ? versions[0].itemIds.filter((id) => versions.slice(1).some((v) => v.itemIds.includes(id))).length
      : 0;
  const versionTotals = versionLabels.map((l) => equivalenceReport?.perVersion?.[l]?.totalMarks as number | undefined);
  const marksParity = versionsAssembled && versionTotals.length > 0 && versionTotals.every((t) => t === targetMarks);
  const dev = equivalenceReport?.deviations || {};
  const pvA = equivalenceReport?.perVersion?.["A"];
  const pvB = equivalenceReport?.perVersion?.["B"];
  const parity = {
    overlap: dev.zeroOverlapGuaranteed === true,
    marks: dev.markDifference === 0,
    count: pvA?.itemCount != null && pvA?.itemCount === pvB?.itemCount,
    clo: dev.cloParity === true,
    bloom: dev.bloomParity === true,
    format: dev.typeParity === true,
  };
  const structuralMismatches = Object.values(parity).filter((ok) => !ok).length;
  const approved = moderationRecord?.decision === "approved";
  const changesRequested = moderationRecord?.decision === "changes_requested";

  const liveChecks = [
    {
      title: "Blueprint totals the target",
      passed: !!blueprint?.valid,
      note: `${currentMarks} of ${targetMarks} marks allocated`,
    },
    {
      title: "Every reviewer flag decided",
      passed: reviewRun && unresolvedFlags.length === 0,
      note: reviewRun ? `${unresolvedFlags.length} of ${flags.length} flags still open` : "Reviewer has not been run",
    },
    {
      title: "Parallel versions assembled",
      passed: versionsAssembled,
      note: `${versions.length} of ${expectedVersions} versions assembled`,
    },
    {
      title: "No question appears in two versions",
      passed: versionsAssembled && sharedItemCount === 0,
      note: versionsAssembled ? `${sharedItemCount} shared questions` : "Needs assembled versions",
    },
    {
      title: "Every version carries the same marks",
      passed: marksParity,
      note: versionsAssembled && versionTotals.length > 0 ? `${versionTotals.map((t) => t ?? "—").join(" / ")} marks` : "Needs assembled versions",
    },
  ];
  const signoffBlockers = liveChecks.filter((c) => !c.passed);
  // Only the QA audit writes the summary; a record without one holds just comments or a decision.
  const qaAudited = !!moderationRecord?.executiveSummary;
  const moderationStale = !!moderationRecord?.stale;
  const readyForSignoff = signoffBlockers.length === 0 && qaAudited && !moderationStale;

  const authorDone = !!blueprint?.valid && items.length > 0;
  const verifyDone = reviewRun && unresolvedFlags.length === 0 && versionsAssembled;
  const stages: StageDef[] = [
    {
      id: "author",
      label: "Author",
      state: authorDone ? "done" : "current",
      summary: authorDone ? `${items.length} questions drafted` : !blueprint?.valid ? "Blueprint needs fixes" : "Pool not drafted",
      tabs: [
        {
          id: "blueprint",
          label: "Blueprint",
          badge: blueprint?.valid ? (
            <Check className="w-3.5 h-3.5 text-emerald-700" aria-label="valid" />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5 text-amber-700" aria-label="needs fixes" />
          ),
        },
        {
          id: "pool",
          label: "Question pool",
          badge: <span className="text-xs px-1.5 rounded-full bg-slate-100 text-slate-700 font-mono">{items.length}</span>,
        },
      ],
    },
    {
      id: "verify",
      label: "Verify",
      state: verifyDone ? "done" : authorDone ? "current" : "todo",
      summary: verifyDone
        ? "Reviewed and assembled"
        : !reviewRun
        ? "Reviewer not run"
        : unresolvedFlags.length > 0
        ? `${unresolvedFlags.length} flags open`
        : "Versions not assembled",
      tabs: [
        {
          id: "review",
          label: "Reviewer audit",
          badge:
            unresolvedFlags.length > 0 ? (
              <span className="text-xs px-1.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-mono font-semibold">
                {unresolvedFlags.length}
              </span>
            ) : reviewRun ? (
              <Check className="w-3.5 h-3.5 text-emerald-700" aria-label="all decided" />
            ) : undefined,
        },
        {
          id: "solver",
          label: "Parallel versions",
          badge: versionsAssembled ? <Check className="w-3.5 h-3.5 text-emerald-700" aria-label="assembled" /> : undefined,
        },
      ],
    },
    {
      id: "signoff",
      label: "Sign off",
      state: approved ? "done" : verifyDone ? "current" : "todo",
      summary: approved
        ? "Approved"
        : changesRequested
        ? "Changes requested"
        : verifyDone
        ? "Awaiting moderator"
        : "Not ready yet",
      tabs: [
        { id: "moderation", label: "Moderation" },
        { id: "export", label: "Export" },
      ],
    },
  ];

  // A user can be a lecturer and a moderator: they sign off only papers assigned to them, never their own.
  const isMyPaper = assessment?.createdByUid ? assessment.createdByUid === user.uid : assessment?.createdBy === user.email;
  const isAssignedModerator = isModerator && !!assessment?.moderatorUid && assessment.moderatorUid === user.uid;
  const canDecide = !isMyPaper && isAssignedModerator;
  // The QA audit is the moderator's independent check; the backend refuses it from anyone else.
  const canRunAudit = canDecide && assessment?.status === "in_moderation";
  const decidingAs = isAssignedModerator ? "moderator" : role;
  const nextAction: NextAction = canDecide && !approved && !changesRequested && !verifyDone
    ? {
        tone: "waiting",
        text: `the lecturer hasn't finished verification (${
          !reviewRun ? "Reviewer not run" : unresolvedFlags.length > 0 ? `${unresolvedFlags.length} flags open` : "versions not assembled"
        }). Approval unlocks when every live check passes.`,
        cta: activeTab !== "moderation" ? { label: "View live checks", onClick: () => goTab("moderation") } : undefined,
      }
    : !blueprint?.valid
    ? {
        tone: "action",
        text: `the blueprint allocates ${currentMarks} of ${targetMarks} marks. Adjust item counts until it adds up.`,
        cta: activeTab !== "blueprint" ? { label: "Open blueprint", onClick: () => goTab("blueprint") } : undefined,
      }
    : items.length === 0
    ? {
        tone: "action",
        text: `draft the question pool (${poolTarget} candidates for ${requiredItemCount} slots).`,
        cta: { label: generatingPool ? "Drafting…" : "Draft pool", onClick: handleGeneratePool, disabled: generatingPool },
      }
    : !reviewRun
    ? {
        tone: "action",
        text: `run the Reviewer over ${items.length} candidate questions before assembling papers.`,
        cta: { label: runningReviewer ? "Reviewing…" : "Run Reviewer", onClick: handleRunReviewer, disabled: runningReviewer },
      }
    : unresolvedFlags.length > 0
    ? {
        tone: "action",
        text: `decide ${unresolvedFlags.length} open reviewer flags across ${new Set(unresolvedFlags.map((f) => f.itemId)).size} questions: keep or reject each one.`,
        cta: activeTab !== "review" ? { label: "Open reviewer audit", onClick: () => goTab("review") } : undefined,
      }
    : !versionsAssembled
    ? {
        tone: "action",
        text: `assemble ${expectedVersions} parallel versions from the cleared pool.`,
        cta: { label: runningSolver ? "Assembling…" : "Assemble versions", onClick: handleRunSolver, disabled: runningSolver },
      }
    : approved
    ? {
        tone: "done",
        text: `approved by ${moderationRecord?.decidedBy}. Download the exam package.`,
        cta: activeTab !== "export" ? { label: "Open export", onClick: () => goTab("export") } : undefined,
      }
    : changesRequested
    ? {
        tone: "action",
        text: `${moderationRecord?.decidedBy} requested changes. Read their notes, fix the paper, then re-run the checks.`,
        cta: activeTab !== "moderation" ? { label: "Read notes", onClick: () => goTab("moderation") } : undefined,
      }
    : canDecide
    ? {
        tone: "action",
        text: "every check passes. Review the package and sign it off.",
        cta: activeTab !== "moderation" ? { label: "Open moderation", onClick: () => goTab("moderation") } : undefined,
      }
    : {
        tone: "waiting",
        text: "every check passes. The package is waiting for the moderator's sign-off.",
        cta: activeTab !== "moderation" ? { label: "View moderation", onClick: () => goTab("moderation") } : undefined,
      };

  const activeVersionItems = versionItems[activeVersionLabel] || [];
  const filteredActiveVersionItems = activeVersionItems.filter((it) => {
    return solverSectionFilter === "all" || it.qType === solverSectionFilter;
  });

  return (
    <div className="min-h-full py-4 text-slate-900 bg-slate-50">
      {/* Assessment Header Banner matching Screen 3 & 4 in Figma */}
      <header className="border-b border-slate-200 bg-white pb-1">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
              <button onClick={() => router.push("/")} className="hover:text-emerald-700 transition">
                Dashboard
              </button>
              <span>/</span>
              <span className="text-slate-700 font-medium">{assessment?.courseId}</span>
              <span>/</span>
              <span className="text-emerald-700 font-mono text-[11px] font-semibold">{assessment?.id}</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                {assessment?.title}
              </h1>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
                  assessment?.status === "assembled"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : assessment?.status === "reviewed" || assessment?.status === "in_moderation"
                    ? "bg-amber-50 text-amber-700 border-amber-200"
                    : "bg-sky-50 text-sky-700 border-sky-200"
                }`}
              >
                ● {assessment?.status === "assembled"
                  ? "Approved"
                  : assessment?.status
                  ? assessment.status.charAt(0).toUpperCase() + assessment.status.slice(1).replace(/_/g, " ")
                  : "Draft"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 whitespace-nowrap text-xs font-mono text-slate-700 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg shadow-xs">
              <span><Target className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> {assessment?.totalMarks} Marks</span>
              <span className="text-slate-300">•</span>
              <span><Timer className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> {assessment?.durationMins} Mins</span>
              <span className="text-slate-300">•</span>
              <span><Layers className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> {assessment?.numVersions} Versions</span>
            </div>

            <button
              onClick={() => setShowShortcuts(true)}
              title="Keyboard shortcuts (?)"
              className="px-2.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 hover:text-slate-800 text-xs font-mono flex items-center gap-1.5 whitespace-nowrap transition shadow-xs cursor-pointer"
            >
              <Keyboard className="w-3.5 h-3.5 text-slate-500" aria-hidden />
              <span className="hidden sm:inline">Shortcuts</span>
              <kbd className="px-1 py-0.2 rounded bg-slate-100 text-[10px] text-slate-500 font-mono">?</kbd>
            </button>

            <button
              onClick={() => setIsTraceOpen(true)}
              className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-emerald-700 hover:text-emerald-800 text-xs font-semibold flex items-center gap-2 whitespace-nowrap transition shadow-xs cursor-pointer"
            >
              <Bot className="w-3.5 h-3.5" aria-hidden />
              <span>Agent Trace</span>
            </button>
          </div>
        </div>

        <StageNav stages={stages} activeTab={activeTab} onSelect={goTab} />
      </header>

      {/* Main Workspace Body */}
      <main
        id="workflow-panel"
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6"
      >
        <div className="space-y-3 mb-6">
          {loadWarnings.length > 0 && (
            <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 flex items-center justify-between gap-3 text-sm text-rose-800">
              <span>Couldn&apos;t load {loadWarnings.join(", ")}. What you see below may be incomplete.</span>
              <button onClick={loadData} className="font-semibold underline cursor-pointer whitespace-nowrap">
                Retry
              </button>
            </div>
          )}
          <NextActionStrip action={nextAction} />
        </div>
        {/* ========================================================================= */}
        {/* TAB 1: BLUEPRINT MATRIX EDITOR                                            */}
        {/* ========================================================================= */}
        {activeTab === "blueprint" && (
          <div className="space-y-6">
            <div
              className={`rounded-xl p-4 sm:p-5 border transition shadow-xs ${
                isMarksValid
                  ? "bg-emerald-50/80 border-emerald-200 text-emerald-900"
                  : "bg-amber-50/80 border-amber-200 text-amber-900"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg ${
                      isMarksValid
                        ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                        : "bg-amber-100 text-amber-700 border border-amber-200"
                    }`}
                  >
                    {isMarksValid ? "✓" : "!"}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-base">
                        Deterministic Rules Verification
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-mono font-medium ${
                          isMarksValid ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {isMarksValid ? "VALIDATED" : "VIOLATION DETECTED"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-0.5">
                      {isMarksValid
                        ? `Allocated marks (${currentMarks}) match the syllabus target (${targetMarks}). Total items: ${requiredItemCount}.`
                        : `Allocated marks sum to ${currentMarks}, but required target is ${targetMarks} marks. Adjust item counts below.`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRegenerateBlueprint}
                    disabled={generatingBp || isLocked}
                    title={lockedTitle}
                    className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 flex items-center gap-1.5 transition shadow-xs disabled:opacity-50 cursor-pointer"
                  >
                    <RefreshCw className="w-4 h-4" aria-hidden />
                    <span>{generatingBp ? "Regenerating..." : "Regenerate"}</span>
                  </button>

                  <button
                    onClick={handleSaveBlueprint}
                    disabled={savingBp || isLocked || !bpDirty}
                    title={lockedTitle}
                    className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-medium text-xs shadow-xs transition disabled:opacity-50 cursor-pointer"
                  >
                    {savingBp ? "Saving..." : bpDirty ? "Save changes" : "Saved"}
                  </button>
                </div>
              </div>

              {blueprint?.violations && blueprint.violations.length > 0 && !isMarksValid && (
                <div className="mt-3 pt-3 border-t border-amber-200 text-xs text-amber-800 space-y-1">
                  {blueprint.violations.map((v, i) => (
                    <div key={i} className="flex items-center gap-1.5">
                      <span>•</span>
                      <span>{v}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className={`${blueprint?.rationale ? "lg:col-span-3" : "lg:col-span-4"} bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden`}>
                <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">
                    Assessment Matrix Specification ({blueprint?.cells?.length || 0} Cells)
                  </h3>
                  <span className="text-xs text-slate-500">
                    Target: {targetMarks} Marks • {poolMultiplier}× Pool Buffer: {poolTarget} candidates
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-4">CLO</th>
                        <th className="py-3 px-3">Topic</th>
                        <th className="py-3 px-3">Bloom</th>
                        <th className="py-3 px-3">Type</th>
                        <th className="py-3 px-3 text-center">Items Needed</th>
                        <th className="py-3 px-3 text-center">Marks Each</th>
                        <th className="py-3 px-4 text-right">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      {blueprint?.cells?.map((cell, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/80 transition">
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                              {cell.cloId}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-800 font-sans font-medium">{cell.topicId}</td>
                          <td className="py-3 px-3 font-sans">
                            <span className={`px-2 py-0.5 rounded text-[11px] border ${getBloomBadgeColor(cell.bloom)}`}>
                              {cell.bloom}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-600 font-sans">
                            {cell.qType === "mcq" ? "MCQ (4 opt)" : QTYPE_LABEL[cell.qType] ?? cell.qType}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <input
                              type="number"
                              aria-label={`Items needed for ${cell.cloId} ${cell.topicId} ${cell.bloom}`}
                              min={0}
                              max={50}
                              disabled={isLocked}
                              value={cell.count}
                              onChange={(e) => handleCellChange(idx, "count", parseInt(e.target.value) || 0)}
                              className="w-14 bg-white border border-slate-200 rounded px-2 py-1 text-center text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 disabled:bg-slate-50 disabled:text-slate-500"
                            />
                          </td>
                          <td className="py-3 px-3 text-center">
                            <input
                              type="number"
                              aria-label={`Marks each for ${cell.cloId} ${cell.topicId} ${cell.bloom}`}
                              min={1}
                              max={50}
                              disabled={isLocked}
                              value={cell.marksEach}
                              onChange={(e) => handleCellChange(idx, "marksEach", parseInt(e.target.value) || 1)}
                              className="w-14 bg-white border border-slate-200 rounded px-2 py-1 text-center text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 disabled:bg-slate-50 disabled:text-slate-500"
                            />
                          </td>
                          <td className="py-3 px-4 text-right font-bold text-slate-900">
                            {cell.count * cell.marksEach}m
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-slate-50 text-slate-800 font-bold border-t border-slate-200">
                      <tr>
                        <td colSpan={4} className="py-3 px-4 text-slate-500">Total Assessment Marks</td>
                        <td className="py-3 px-3 text-center text-emerald-700">{requiredItemCount} items</td>
                        <td className="py-3 px-3"></td>
                        <td className={`py-3 px-4 text-right ${isMarksValid ? "text-emerald-700" : "text-amber-700"}`}>
                          {currentMarks} / {targetMarks}m
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Drafting the pool lives in the Next strip; this column only explains the blueprint. */}
              {blueprint?.rationale && (
                <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3 self-start">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    <Brain className="w-4 h-4" aria-hidden />
                    <span>Pedagogical Rationale</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">{blueprint.rationale}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: CANDIDATE ITEM POOL                                    */}
        {/* ========================================================================= */}
        {activeTab === "pool" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900">Candidate Item Pool</h3>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                    {poolItemCount} Items Generated
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Blueprint requires {requiredItemCount} items. Available pool provides a{" "}
                  <strong className="text-emerald-700 font-mono font-bold">{bufferMultiplier}×</strong> candidate buffer for
                  automated reviewer audit and OR-Tools multi-version assembly.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleGeneratePool}
                  disabled={generatingPool || isLocked}
                  title={lockedTitle}
                  className="px-4 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 flex items-center gap-2 transition shadow-xs disabled:opacity-50 cursor-pointer whitespace-nowrap"
                >
                  <RefreshCw className="w-4 h-4" aria-hidden />
                  <span>{generatingPool ? "Drafting..." : "Re-Draft Pool"}</span>
                </button>

                <button
                  onClick={() => goTab("review")}
                  className="px-4 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold text-xs shadow-xs transition cursor-pointer whitespace-nowrap flex items-center gap-1.5"
                >
                  <span><Search className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> Reviewer audit</span>
                  <span>→</span>
                </button>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
              <div className="w-full md:w-80">
                <input
                  type="text"
                  aria-label="Search questions"
                  placeholder="Search questions or keywords..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3.5 py-2 text-xs text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600"
                />
              </div>

              <div className="flex flex-wrap gap-2 w-full md:w-auto">
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-700 focus:outline-none focus:border-emerald-600"
                >
                  <option value="all">All Types</option>
                  <option value="mcq">MCQ Only</option>
                  <option value="short_answer">Structured</option>
                  <option value="essay">Free Response</option>
                </select>

                <select
                  value={filterBloom}
                  onChange={(e) => setFilterBloom(e.target.value)}
                  className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-700 focus:outline-none focus:border-emerald-600"
                >
                  <option value="all">All Bloom Levels</option>
                  <option value="remember">Remember</option>
                  <option value="understand">Understand</option>
                  <option value="apply">Apply</option>
                  <option value="analyse">Analyse</option>
                  <option value="evaluate">Evaluate</option>
                  <option value="create">Create</option>
                </select>

                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-700 focus:outline-none focus:border-emerald-600"
                >
                  <option value="all">All Statuses</option>
                  <option value="candidate">Candidate Only</option>
                  <option value="accepted">Accepted Only</option>
                  <option value="rejected">Rejected Only</option>
                </select>

                {(() => {
                  const pending = filteredItems.filter((it) => it.status === "candidate").map((it) => it.id);
                  return (
                    <button
                      onClick={() => handleAcceptAll(pending)}
                      disabled={pending.length === 0 || isLocked}
                      className="px-3 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer whitespace-nowrap"
                    >
                      Accept all{pending.length > 0 ? ` (${pending.length})` : ""}
                    </button>
                  );
                })()}
              </div>
            </div>

            {filteredItems.length === 0 ? (
              <div className="bg-white rounded-xl p-12 text-center border border-slate-200/90 shadow-xs space-y-3">
                <ClipboardList className="w-8 h-8 mx-auto text-slate-500" aria-hidden />
                <h2 className="text-sm font-bold text-slate-900">No questions to show</h2>
                <p className="text-xs text-slate-600 max-w-sm mx-auto">
                  {items.length === 0
                    ? "The question pool hasn't been drafted yet."
                    : "No questions match these filters."}
                </p>
              </div>
            ) : (
              <ol className="bg-white rounded-xl border border-slate-200/90 shadow-xs divide-y divide-slate-100">
                {filteredItems.map((item) => {
                  const open = expandedRationales[item.id] || false;
                  const qName = `Q${items.indexOf(item) + 1}`;
                  const openFlags = unresolvedFlags.filter((f) => f.itemId === item.id).length;
                  const rejected = item.status === "rejected";

                  return (
                    <li key={item.id} className={`p-4 ${rejected ? "bg-slate-50" : ""}`}>
                      <div className="flex flex-col md:flex-row md:items-start gap-3">
                        <span className="font-mono text-xs text-slate-500 w-10 shrink-0 pt-0.5">{qName}</span>
                        <div className="flex-1 min-w-0">
                          <p
                            className={`text-sm leading-relaxed ${open ? "" : "line-clamp-2"} ${
                              rejected ? "text-slate-500 line-through" : "text-slate-900"
                            }`}
                          >
                            {item.stem}
                          </p>
                          <div className="flex flex-wrap items-center gap-1.5 mt-2 text-xs text-slate-600">
                            <span className="font-mono">{item.marks} marks</span>
                            <span className="font-mono px-1.5 rounded bg-slate-100 text-slate-700">{item.cloId}</span>
                            <span className={`px-1.5 rounded border ${getBloomBadgeColor(item.bloom)}`}>{item.bloom}</span>
                            <span>{QTYPE_LABEL[item.qType] ?? item.qType}</span>
                            <span className="font-mono">Difficulty {item.difficulty}/5</span>
                            {openFlags > 0 && (
                              <button
                                onClick={() => goTab("review")}
                                className="px-1.5 rounded bg-amber-50 text-amber-800 border border-amber-200 cursor-pointer"
                              >
                                {openFlags} open {openFlags === 1 ? "flag" : "flags"}
                              </button>
                            )}
                            <button
                              onClick={() => toggleRationale(item.id)}
                              aria-expanded={open}
                              className="ml-1 text-emerald-800 font-medium inline-flex items-center gap-1 cursor-pointer"
                            >
                              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
                              {open ? "Hide details" : "Details"}
                            </button>
                          </div>

                          {open && (
                            <div className="mt-3 space-y-3">
                              {item.qType === "mcq" && item.options && (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  {item.options.map((opt) => {
                                    const isKey = opt.id === item.key;
                                    return (
                                      <div
                                        key={opt.id}
                                        className={`p-2.5 rounded-lg border text-xs flex gap-2 ${
                                          isKey ? "bg-emerald-50 border-emerald-300 text-emerald-950 font-medium" : "bg-slate-50 border-slate-200 text-slate-700"
                                        }`}
                                      >
                                        <span className="font-bold">{opt.id}.</span>
                                        <span className="flex-1">{opt.text}</span>
                                        {isKey && <span className="font-semibold text-emerald-800">Key</span>}
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                              {item.qType === "short_answer" && (
                                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                                  <span className="text-slate-700 font-semibold block mb-1">Model answer and marking rubric</span>
                                  <div className="text-slate-800 whitespace-pre-line font-mono">{item.key}</div>
                                </div>
                              )}
                              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
                                <span className="font-semibold block mb-1">Rationale and distractor analysis</span>
                                <div className="whitespace-pre-line leading-relaxed">{item.rationale}</div>
                              </div>
                              {item.sourceCitations?.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 items-center text-xs">
                                  <span className="text-slate-600">Sources:</span>
                                  {item.sourceCitations.map((cit, cIdx) => (
                                    <span
                                      key={cIdx}
                                      className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 truncate max-w-xs"
                                      title={`${cit.title || cit.docId}: ${cit.snippet}`}
                                    >
                                      <FileText className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> {cit.title || cit.docId}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* A decided question shows its status as text, not as a pressed button; only undecided ones get actions. */}
                        <div className="flex items-center gap-2 shrink-0">
                          {item.status === "accepted" || rejected ? (
                            <>
                              <span
                                className={`inline-flex items-center gap-1 text-xs font-semibold ${
                                  rejected ? "text-rose-700" : "text-emerald-700"
                                }`}
                              >
                                {rejected ? <X className="w-3.5 h-3.5" aria-hidden /> : <Check className="w-3.5 h-3.5" aria-hidden />}
                                {rejected ? "Rejected" : "Accepted"}
                              </span>
                              {!isLocked && (
                                <button
                                  onClick={() => handleUpdateItemStatus(item.id, "candidate")}
                                  aria-label={`Undo decision on ${qName}`}
                                  className="text-xs text-slate-500 hover:text-slate-800 underline underline-offset-2 cursor-pointer"
                                >
                                  Undo
                                </button>
                              )}
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => handleUpdateItemStatus(item.id, "accepted")}
                                disabled={isLocked}
                                aria-label={`Accept ${qName}`}
                                className="px-2.5 py-1 rounded-lg text-xs font-medium border transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed bg-white text-slate-700 border-slate-200 hover:border-emerald-600"
                              >
                                Accept
                              </button>
                              <button
                                onClick={() => handleUpdateItemStatus(item.id, "rejected")}
                                disabled={isLocked}
                                aria-label={`Reject ${qName}`}
                                className="px-2.5 py-1 rounded-lg text-xs font-medium border transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed bg-white text-slate-700 border-slate-200 hover:border-rose-600"
                              >
                                Reject
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: REVIEWER AUDIT (MILESTONE 4)                                       */}
        {/* ========================================================================= */}
        {activeTab === "review" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 font-bold">
                      <Search className="w-5 h-5" aria-hidden />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">Adversarial Reviewer Audit</h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Solves each question blind without answer keys (3 independent runs) to catch ambiguity, and checks embeddings cosine similarity (&ge; 88%) against the past exam corpus.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-start gap-3">
                  <button
                    onClick={handleRunReviewer}
                    disabled={runningReviewer || isLocked}
                    title={lockedTitle}
                    className="px-4 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs shadow-xs flex items-center gap-2 transition disabled:opacity-50 cursor-pointer whitespace-nowrap"
                  >
                    {runningReviewer ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
                        <span>Reviewer Auditing Items...</span>
                      </>
                    ) : (
                      <>
                        <span><Zap className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> Run Adversarial Reviewer</span>
                        <RefreshCw className="w-4 h-4" aria-hidden />
                      </>
                    )}
                  </button>

                  <div className="flex flex-col items-start sm:items-end gap-1">
                    <button
                      onClick={() => goTab("solver")}
                      disabled={unresolvedFlags.length > 0}
                      aria-describedby={unresolvedFlags.length > 0 ? "proceed-reason" : undefined}
                      className="px-4 py-2.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 font-semibold text-xs shadow-xs transition cursor-pointer whitespace-nowrap flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span>Proceed to parallel versions</span>
                      <span aria-hidden>→</span>
                    </button>
                    {unresolvedFlags.length > 0 && (
                      <span id="proceed-reason" className="text-xs text-slate-600">
                        Decide the {unresolvedFlags.length} open flags first
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[11px] text-slate-500 uppercase tracking-wider block mb-1">Total Flags</span>
                  <span className="text-2xl font-bold font-mono text-slate-900">{flags.length}</span>
                </div>

                <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200">
                  <span className="text-[11px] text-rose-700 uppercase tracking-wider block mb-1">Key Conflicts</span>
                  <span className="text-2xl font-bold font-mono text-rose-700">{keyMismatchCount}</span>
                </div>

                <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200">
                  <span className="text-[11px] text-amber-700 uppercase tracking-wider block mb-1">Past Duplicates</span>
                  <span className="text-2xl font-bold font-mono text-amber-700">{pastDuplicateCount}</span>
                </div>

                <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200">
                  <span className="text-[11px] text-sky-700 uppercase tracking-wider block mb-1">Pool Duplicates</span>
                  <span className="text-2xl font-bold font-mono text-sky-700">{poolDuplicateCount}</span>
                </div>

                <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200">
                  <span className="text-[11px] text-amber-700 uppercase tracking-wider block mb-1">Item Flaws</span>
                  <span className="text-2xl font-bold font-mono text-amber-700">{flawCount}</span>
                </div>

                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200">
                  <span className="text-[11px] text-emerald-700 uppercase tracking-wider block mb-1">Clean Items</span>
                  <span className="text-2xl font-bold font-mono text-emerald-700">{cleanItemsCount}</span>
                </div>
              </div>
            </div>

            {(() => {
              const sevRank = { high: 0, medium: 1, low: 2 } as const;
              const groups = Object.values(
                filteredFlags.reduce<Record<string, Flag[]>>((acc, f) => {
                  (acc[f.itemId] ||= []).push(f);
                  return acc;
                }, {})
              )
                .map((fl) => {
                  const sorted = [...fl].sort((x, y) => sevRank[x.severity] - sevRank[y.severity]);
                  const item = items.find((it) => it.id === sorted[0].itemId);
                  return {
                    itemId: sorted[0].itemId,
                    flags: sorted,
                    open: sorted.filter((f) => !f.resolution),
                    item,
                    qName: item ? `Q${items.indexOf(item) + 1}` : sorted[0].itemId,
                  };
                })
                .sort((x, y) => sevRank[x.flags[0].severity] - sevRank[y.flags[0].severity] || y.flags.length - x.flags.length);
              const selectable = groups.filter((g) => g.open.length > 0);
              const selected = selectable.filter((g) => selectedFlagItems[g.itemId]);
              const allSelected = selectable.length > 0 && selected.length === selectable.length;
              const openIds = (gs: typeof groups) => gs.flatMap((g) => g.open.map((f) => f.id));
              const keep = (gs: typeof groups) =>
                resolveFlags(
                  openIds(gs),
                  "dismissed",
                  "Kept by lecturer after review",
                  gs.length === 1 ? `Kept ${gs[0].qName}.` : `Kept ${gs.length} questions.`
                );
              const reject = (gs: typeof groups) =>
                resolveFlags(
                  openIds(gs),
                  "accepted",
                  "Accepted flag, reject flawed/duplicate item",
                  gs.length === 1 ? `Rejected ${gs[0].qName}.` : `Rejected ${gs.length} questions.`
                );

              return (
                <>
                  <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-xs flex flex-wrap gap-3 items-center justify-between">
                    <div className="flex items-center gap-3">
                      {selectable.length > 0 && (
                        <input
                          type="checkbox"
                          aria-label="Select all questions shown"
                          checked={allSelected}
                          onChange={() =>
                            setSelectedFlagItems(allSelected ? {} : Object.fromEntries(selectable.map((g) => [g.itemId, true])))
                          }
                          className="w-4 h-4 accent-emerald-700"
                        />
                      )}
                      {selected.length > 0 ? (
                        <div className="flex items-center gap-2 text-sm">
                          <span className="font-semibold text-slate-900">{selected.length} selected</span>
                          <button
                            onClick={() => keep(selected)}
                            className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800 cursor-pointer"
                          >
                            Keep {selected.length}
                          </button>
                          <button
                            onClick={() => reject(selected)}
                            className="px-3 py-1.5 rounded-lg bg-white hover:bg-rose-50 border border-rose-300 text-xs font-semibold text-rose-800 cursor-pointer"
                          >
                            Reject {selected.length}
                          </button>
                        </div>
                      ) : (
                        <span className="text-sm text-slate-700">
                          <span className="font-mono font-semibold">{groups.length}</span> questions ·{" "}
                          <span className="font-mono">{filteredFlags.length}</span> flags
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => keep(selectable)}
                        disabled={selectable.length === 0}
                        className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer whitespace-nowrap"
                      >
                        Keep all{selectable.length > 0 ? ` (${selectable.length})` : ""}
                      </button>
                      <select
                        aria-label="Flag type"
                        value={flagFilterType}
                        onChange={(e) => setFlagFilterType(e.target.value)}
                        className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800"
                      >
                        <option value="all">All flag types</option>
                        <option value="key_mismatch">Key mismatches</option>
                        <option value="duplicate_past">Past exam duplicates</option>
                        <option value="duplicate_pool">Pool duplicates</option>
                        <option value="item_flaw">Item flaws</option>
                        <option value="bloom_doubt">Bloom doubts</option>
                      </select>
                      <select
                        aria-label="Severity"
                        value={flagFilterSeverity}
                        onChange={(e) => setFlagFilterSeverity(e.target.value)}
                        className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800"
                      >
                        <option value="all">All severities</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>
                      <select
                        aria-label="Decision status"
                        value={flagFilterStatus}
                        onChange={(e) => setFlagFilterStatus(e.target.value)}
                        className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800"
                      >
                        <option value="unresolved">Needs a decision</option>
                        <option value="resolved">Decided</option>
                        <option value="all">All</option>
                      </select>
                    </div>
                  </div>

                  {groups.length === 0 ? (
                    <div className="bg-white rounded-xl p-12 text-center border border-slate-200/90 shadow-xs space-y-3">
                      <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-700" aria-hidden />
                      <h2 className="text-base font-semibold text-slate-900">
                        {!reviewRun ? "The Reviewer hasn't run yet" : flagFilterStatus === "unresolved" ? "Nothing left to decide" : "No flags match"}
                      </h2>
                      <p className="text-xs text-slate-600 max-w-sm mx-auto">
                        {!reviewRun
                          ? "Run the Reviewer to blind-solve every question and check it against past papers."
                          : flagFilterStatus === "unresolved"
                          ? "Every reviewer flag has a decision. Assemble the parallel versions next."
                          : "Try a different filter."}
                      </p>
                    </div>
                  ) : (
                    <ol className="bg-white rounded-xl border border-slate-200/90 shadow-xs divide-y divide-slate-100">
                      {groups.map((g) => {
                        const expanded = expandedFlagItems[g.itemId] || false;
                        const top = g.flags[0];
                        const typeCounts = g.flags.reduce<Record<string, number>>((acc, f) => {
                          acc[f.type] = (acc[f.type] || 0) + 1;
                          return acc;
                        }, {});
                        const decided = g.open.length === 0;
                        const wasRejected = decided && g.flags.some((f) => f.resolution === "accepted");
                        const hasMismatch = g.open.some((f) => f.type === "key_mismatch");

                        return (
                          <li key={g.itemId} className={`p-4 ${decided ? "bg-slate-50" : ""}`}>
                            <div className="flex items-start gap-3">
                              {!decided ? (
                                <input
                                  type="checkbox"
                                  aria-label={`Select ${g.qName}`}
                                  checked={!!selectedFlagItems[g.itemId]}
                                  onChange={(e) => setSelectedFlagItems((prev) => ({ ...prev, [g.itemId]: e.target.checked }))}
                                  className="w-4 h-4 mt-1 accent-emerald-700"
                                />
                              ) : (
                                <span className="w-4" />
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-1.5 mb-1.5 text-xs">
                                  <span className="font-mono text-slate-500">{g.qName}</span>
                                  <span
                                    className={`px-1.5 rounded font-semibold uppercase ${
                                      top.severity === "high"
                                        ? "bg-rose-50 text-rose-800 border border-rose-200"
                                        : top.severity === "medium"
                                        ? "bg-amber-50 text-amber-800 border border-amber-200"
                                        : "bg-slate-100 text-slate-700 border border-slate-200"
                                    }`}
                                  >
                                    {top.severity}
                                  </span>
                                  {Object.entries(typeCounts).map(([type, n]) => {
                                    const badge = getFlagBadge(type);
                                    return (
                                      <span key={type} className={`inline-flex items-center gap-1 px-1.5 rounded-full border ${badge.color}`}>
                                        <badge.Icon className="w-3 h-3" aria-hidden />
                                        {badge.label}
                                        {n > 1 && <span className="font-mono">×{n}</span>}
                                      </span>
                                    );
                                  })}
                                  {decided && (
                                    <span className={`px-1.5 rounded-full border ${wasRejected ? "bg-rose-50 text-rose-800 border-rose-200" : "bg-emerald-50 text-emerald-800 border-emerald-200"}`}>
                                      {wasRejected ? "Rejected" : "Kept"}
                                      {top.resolvedBy ? ` by ${top.resolvedBy}` : ""}
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-slate-900 line-clamp-2">{g.item?.stem ?? "Question text unavailable"}</p>
                                <p className="text-xs text-slate-600 mt-1 line-clamp-2">{top.detail}</p>
                                <button
                                  onClick={() => setExpandedFlagItems((prev) => ({ ...prev, [g.itemId]: !expanded }))}
                                  aria-expanded={expanded}
                                  className="mt-1.5 text-xs text-emerald-800 font-medium inline-flex items-center gap-1 cursor-pointer"
                                >
                                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} aria-hidden />
                                  {expanded ? "Hide evidence" : g.flags.length > 1 ? `Evidence for ${g.flags.length} flags` : "Evidence"}
                                </button>

                                {expanded && (
                                  <div className="mt-3 space-y-3">
                                    {g.item?.qType === "mcq" && g.item.options && (
                                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                                        {g.item.options.map((o) => (
                                          <div
                                            key={o.id}
                                            className={`p-2 rounded-lg border ${
                                              o.id === g.item?.key ? "bg-emerald-50 border-emerald-300 text-emerald-950 font-semibold" : "bg-white border-slate-200 text-slate-700"
                                            }`}
                                          >
                                            <strong>{o.id}.</strong> {o.text} {o.id === g.item?.key ? "(author key)" : ""}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                    {g.flags.map((f) => {
                                      const twinIds = Array.from(
                                        new Set(`${f.detail} ${f.evidence || ""}`.match(/item-[0-9a-f]{6,}/g) || [])
                                      ).filter((id) => id !== f.itemId);
                                      const twins = twinIds.map((id) => items.find((it) => it.id === id)).filter(Boolean) as Item[];
                                      return (
                                        <div key={f.id} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-2">
                                          <p className="text-slate-800">
                                            <strong className="text-slate-900">{getFlagBadge(f.type).label}: </strong>
                                            {f.detail}
                                          </p>
                                          {twins.length > 0 ? (
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                              <div className="p-2.5 rounded-md bg-white border border-slate-200">
                                                <span className="block text-slate-600 mb-1">This question ({g.qName})</span>
                                                <p className="text-slate-900">{g.item?.stem}</p>
                                              </div>
                                              {twins.map((t) => (
                                                <div key={t.id} className="p-2.5 rounded-md bg-white border border-amber-200">
                                                  <span className="block text-amber-800 mb-1">
                                                    Near-duplicate (Q{items.indexOf(t) + 1}, {t.status})
                                                  </span>
                                                  <p className="text-slate-900">{t.stem}</p>
                                                </div>
                                              ))}
                                            </div>
                                          ) : (
                                            f.evidence && (
                                              <div className="text-slate-800 bg-white p-2.5 rounded-md border border-slate-200 font-mono leading-relaxed">
                                                {f.evidence}
                                              </div>
                                            )
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>

                              {!decided && (
                                <div className="flex flex-col sm:flex-row gap-2 shrink-0">
                                  {hasMismatch && (
                                    <button
                                      onClick={() =>
                                        resolveFlags(
                                          g.open.filter((f) => f.type === "key_mismatch").map((f) => f.id),
                                          "accepted",
                                          "Accepted mismatch, adopt solved key",
                                          `Adopted the reviewer's key for ${g.qName}.`
                                        )
                                      }
                                      aria-label={`Adopt reviewer key for ${g.qName}`}
                                      className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-medium text-xs cursor-pointer"
                                    >
                                      Adopt key
                                    </button>
                                  )}
                                  <button
                                    onClick={() => keep([g])}
                                    aria-label={`Keep ${g.qName}`}
                                    className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 text-xs font-medium cursor-pointer"
                                  >
                                    Keep
                                  </button>
                                  <button
                                    onClick={() => reject([g])}
                                    aria-label={`Reject ${g.qName}`}
                                    className="px-3 py-1.5 rounded-lg bg-white hover:bg-rose-50 text-rose-800 border border-rose-300 text-xs font-medium cursor-pointer"
                                  >
                                    Reject
                                  </button>
                                </div>
                              )}
                            </div>
                          </li>
                        );
                      })}
                    </ol>
                  )}
                </>
              );
            })()}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: MULTI-VERSION SOLVER (MILESTONE 5)                                 */}
        {/* ========================================================================= */}
        {activeTab === "solver" && (
          <div className="space-y-6">
            {/* Solver Overview Banner */}
            <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 font-bold">
                      <Settings className="w-5 h-5" aria-hidden />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-bold text-slate-900">OR-Tools CP-SAT Paper Assembly</h3>
                        {equivalenceReport && (
                          <span
                            className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold border ${
                              equivalenceReport.solverStatus === "OPTIMAL"
                                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                : equivalenceReport.solverStatus === "FEASIBLE"
                                ? "bg-sky-50 text-sky-700 border-sky-200"
                                : "bg-slate-100 text-slate-700 border-slate-200"
                            }`}
                          >
                            {equivalenceReport.solverStatus}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        OR-Tools CP-SAT exact constraint satisfaction solver. Guarantees 0 mark delta across CLOs and zero question overlap between Paper A &amp; B; difficulty balance is optimized within &plusmn;10% bounds.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleRunSolver}
                    disabled={runningSolver || isLocked}
                    title={lockedTitle}
                    className="px-4 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs shadow-xs flex items-center gap-2 transition disabled:opacity-50 cursor-pointer whitespace-nowrap"
                  >
                    {runningSolver ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
                        <span>Assembling versions…</span>
                      </>
                    ) : (
                      <>
                        <span><Zap className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> Run CP-SAT Assembly</span>
                        <RefreshCw className="w-4 h-4" aria-hidden />
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Equivalence Summary Metric Cards */}
              {equivalenceReport && equivalenceReport.perVersion && Object.keys(equivalenceReport.perVersion).length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[11px] text-slate-500 uppercase tracking-wider block mb-1">
                      Assembled Versions
                    </span>
                    <span className="text-2xl font-bold font-mono text-slate-900">
                      {versions.length} ({versions.map((v) => v.label).join(", ")})
                    </span>
                  </div>

                  <div className={`p-3.5 rounded-xl border ${parity.overlap ? "bg-emerald-50 border-emerald-200" : "bg-rose-50 border-rose-200"}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-[11px] uppercase tracking-wider ${parity.overlap ? "text-emerald-800" : "text-rose-800"}`}>
                        Shared questions
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[11px] font-semibold ${parity.overlap ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                        {parity.overlap ? "Verified" : "Failed"}
                      </span>
                    </div>
                    <span className={`text-2xl font-bold font-mono ${parity.overlap ? "text-emerald-700" : "text-rose-700"}`}>
                      {parity.overlap ? "0 shared" : "Overlap found"}
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] text-sky-700 uppercase tracking-wider">
                        Difficulty Spread (Δ)
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-800">
                        Estimated
                      </span>
                    </div>
                    <span className="text-2xl font-bold font-mono text-sky-700">
                      ±{equivalenceReport.deviations?.difficultySpread ?? 0} pts
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] text-slate-600 uppercase tracking-wider">
                        Solve Time
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">
                        CP-SAT
                      </span>
                    </div>
                    <span className="text-2xl font-bold font-mono text-slate-800">
                      {equivalenceReport.perVersion["A"]?.solveTimeMs ?? "—"} ms
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Equivalence Visual Charts: Recharts Bars by CLO and Bloom's Level */}
            {equivalenceReport && equivalenceReport.perVersion && Object.keys(equivalenceReport.perVersion).length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Chart 1: CLO Marks Allocation */}
                <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-5 flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-xs font-semibold text-slate-900 tracking-wide">
                        CLO marks per version
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Marks allocated to each Course Learning Outcome
                      </p>
                    </div>
                    {versionLabels.length > 1 && (<span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border whitespace-nowrap ${parity.clo ? "bg-emerald-50 text-emerald-800 border-emerald-200" : "bg-rose-50 text-rose-800 border-rose-200"}`}>
                      {parity.clo ? "Equal in every version" : "Differs between versions"}
                    </span>)}
                  </div>

                  <div className="w-full h-64">
                    {cloChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={cloChartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.8} />
                          <XAxis dataKey="clo" stroke="#64748b" fontSize={11} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={11} tickLine={false} unit="m" />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#ffffff",
                              borderColor: "#e2e8f0",
                              borderRadius: "0.5rem",
                              color: "#0f172a",
                              fontSize: "12px",
                              boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                          {versionLabels.map((lbl) => (
                            <Bar
                              key={lbl}
                              dataKey={`Version ${lbl}`}
                              fill={versionColors[lbl] || "#94a3b8"}
                              radius={[4, 4, 0, 0]}
                              isAnimationActive={false}
                            />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-xs text-slate-500">
                        No CLO breakdown data available
                      </div>
                    )}
                  </div>
                </div>

                {/* Chart 2: Bloom's Cognitive Taxonomy Breakdown */}
                <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-5 flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-xs font-semibold text-slate-900 tracking-wide">
                        Bloom level marks per version
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Marks at each cognitive level
                      </p>
                    </div>
                    {versionLabels.length > 1 && (<span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border whitespace-nowrap ${parity.bloom ? "bg-emerald-50 text-emerald-800 border-emerald-200" : "bg-rose-50 text-rose-800 border-rose-200"}`}>
                      {parity.bloom ? "Equal in every version" : "Differs between versions"}
                    </span>)}
                  </div>

                  <div className="w-full h-64">
                    {bloomChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={bloomChartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.8} />
                          <XAxis dataKey="bloom" stroke="#64748b" fontSize={11} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={11} tickLine={false} unit="m" />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#ffffff",
                              borderColor: "#e2e8f0",
                              borderRadius: "0.5rem",
                              color: "#0f172a",
                              fontSize: "12px",
                              boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                          {versionLabels.map((lbl) => (
                            <Bar
                              key={lbl}
                              dataKey={`Version ${lbl}`}
                              fill={versionColors[lbl] || "#94a3b8"}
                              radius={[4, 4, 0, 0]}
                              isAnimationActive={false}
                            />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-xs text-slate-500">
                        No Bloom taxonomy distribution data available
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Side-by-Side Equivalence Comparability Table */}
            {equivalenceReport && equivalenceReport.perVersion && Object.keys(equivalenceReport.perVersion).length > 1 && (
              <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
                <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900">
                    Version comparison
                  </h3>
                  <span className={`text-xs font-medium ${structuralMismatches === 0 ? "text-emerald-800" : "text-rose-700"}`}>
                    {structuralMismatches === 0
                      ? "Structure matches across versions"
                      : `${structuralMismatches} structural ${structuralMismatches === 1 ? "check differs" : "checks differ"}`}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider text-[11px] border-b border-slate-200">
                      <tr>
                        <th className="py-3 px-4 font-semibold">Check</th>
                        <th className="py-3 px-3 text-center font-semibold">Version A (Main Exam)</th>
                        <th className="py-3 px-3 text-center font-semibold">Version B (Repeat Exam)</th>
                        <th className="py-3 px-4 text-right font-semibold">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono">
                      <tr>
                        <td className="py-3 px-4 font-sans text-slate-800">
                          Total marks
                          <span className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-slate-50 text-slate-700 border border-slate-200 ml-2">
                            Hard constraint
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center text-slate-900 font-bold">
                          {equivalenceReport.perVersion["A"]?.totalMarks} Marks
                        </td>
                        <td className="py-3 px-3 text-center text-slate-900 font-bold">
                          {equivalenceReport.perVersion["B"]?.totalMarks} Marks
                        </td>
                        <td className={`py-3 px-4 text-right font-sans font-medium ${parity.marks ? "text-emerald-800" : "text-rose-700"}`}>
                          {parity.marks ? "Equal totals" : "Totals differ"}
                        </td>
                      </tr>

                      <tr>
                        <td className="py-3 px-4 font-sans text-slate-800">
                          Question count
                          <span className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-slate-50 text-slate-700 border border-slate-200 ml-2">
                            Hard constraint
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center text-slate-900 font-bold">
                          {equivalenceReport.perVersion["A"]?.itemCount} Questions
                        </td>
                        <td className="py-3 px-3 text-center text-slate-900 font-bold">
                          {equivalenceReport.perVersion["B"]?.itemCount} Questions
                        </td>
                        <td className={`py-3 px-4 text-right font-sans font-medium ${parity.count ? "text-emerald-800" : "text-rose-700"}`}>
                          {parity.count ? "Same length" : "Lengths differ"}
                        </td>
                      </tr>

                      <tr>
                        <td className="py-3 px-4 font-sans text-slate-800">
                          Shared questions
                          <span className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-slate-50 text-slate-700 border border-slate-200 ml-2">
                            Hard constraint
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center text-slate-700">{pvA?.itemCount ?? "—"} questions</td>
                        <td className="py-3 px-3 text-center text-slate-700">{pvB?.itemCount ?? "—"} questions</td>
                        <td className={`py-3 px-4 text-right font-sans font-medium ${parity.overlap ? "text-emerald-800" : "text-rose-700"}`}>
                          {parity.overlap ? "No shared questions" : "Questions shared"}
                        </td>
                      </tr>

                      <tr>
                        <td className="py-3 px-4 font-sans text-slate-800">
                          Mean difficulty (1–5)
                          <span className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-amber-50 text-amber-700 border border-amber-200 ml-2">
                            Estimated
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center text-slate-900 font-bold">
                          {equivalenceReport.perVersion["A"]?.meanDifficulty} / 5.0
                        </td>
                        <td className="py-3 px-3 text-center text-slate-900 font-bold">
                          {equivalenceReport.perVersion["B"]?.meanDifficulty} / 5.0
                        </td>
                        <td className="py-3 px-4 text-right font-sans text-slate-700 font-medium">
                          Gap {equivalenceReport.deviations?.difficultySpread ?? 0} (estimate)
                        </td>
                      </tr>

                      <tr>
                        <td className="py-3 px-4 font-sans text-slate-800">
                          Question format
                          <span className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-slate-50 text-slate-700 border border-slate-200 ml-2">
                            Hard constraint
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center text-slate-700">
                          {fmtTypeBreakdown(equivalenceReport.perVersion["A"]?.typeCountBreakdown)}
                        </td>
                        <td className="py-3 px-3 text-center text-slate-700">
                          {fmtTypeBreakdown(equivalenceReport.perVersion["B"]?.typeCountBreakdown)}
                        </td>
                        <td className={`py-3 px-4 text-right font-sans font-medium ${parity.format ? "text-emerald-800" : "text-rose-700"}`}>
                          {parity.format ? "Same format split" : "Format split differs"}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Verified properties and limits */}
                <div className="p-4 bg-slate-50 border-t border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider block">
                      Verified in these versions
                    </span>
                    <ul className="text-xs text-slate-700 space-y-1">
                      {equivalenceReport.guaranteed?.map((g, i) => (
                        <li key={i} className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-700 shrink-0" aria-hidden />
                          <span>{g.replace(/\s*\(Guaranteed\)$/, "")}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider block">
                      What this does not prove
                    </span>
                    <ul className="text-xs text-slate-600 space-y-1 leading-relaxed">
                      {equivalenceReport.limitations?.map((l, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <Info className="w-3.5 h-3.5 mt-0.5 text-amber-700 shrink-0" aria-hidden />
                          <span>{l}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Version Paper Preview Inspector */}
            {versions.length > 0 ? (
              <div className="space-y-4">
                {/* Version Selector Tabs & Controls */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white rounded-xl p-4 border border-slate-200/90 shadow-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-600 font-medium">Select Paper Version:</span>
                    <div className="flex gap-1.5">
                      {versions.map((ver) => (
                        <button
                          key={ver.id}
                          onClick={() => setActiveVersionLabel(ver.label)}
                          className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                            activeVersionLabel === ver.label
                              ? "bg-emerald-700 text-white shadow-xs"
                              : "bg-white hover:bg-slate-50 text-slate-700 border border-slate-200"
                          }`}
                        >
                          Version {ver.label} ({ver.label === "A" ? "Main Exam" : "Repeat Exam"})
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex gap-1 text-xs bg-slate-50 p-1 rounded-lg border border-slate-200">
                      <button
                        onClick={() => setSolverSectionFilter("all")}
                        className={`px-2.5 py-1 rounded-md transition cursor-pointer ${
                          solverSectionFilter === "all" ? "bg-white text-slate-900 font-semibold shadow-xs" : "text-slate-600"
                        }`}
                      >
                        All ({activeVersionItems.length})
                      </button>
                      {QTYPE_ORDER.filter((qt) => activeVersionItems.some((it) => it.qType === qt)).map((qt, i) => (
                        <button
                          key={qt}
                          onClick={() => setSolverSectionFilter(qt)}
                          className={`px-2.5 py-1 rounded-md transition cursor-pointer ${
                            solverSectionFilter === qt ? "bg-white text-slate-900 font-semibold shadow-xs" : "text-slate-600"
                          }`}
                        >
                          Section {String.fromCharCode(65 + i)}: {QTYPE_LABEL[qt]}
                        </button>
                      ))}
                    </div>

                    <button
                      onClick={() => setShowAnswerKeys(!showAnswerKeys)}
                      className={`px-3 py-1.5 rounded-lg text-xs border transition cursor-pointer ${
                        showAnswerKeys
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold"
                          : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      {showAnswerKeys ? "✓ Marking Guide Visible" : "Show Answers & Rubric"}
                    </button>
                  </div>
                </div>

                {/* Formatted Examination Paper View */}
                <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-6 sm:p-8 space-y-8">
                  {/* Exam Paper Header */}
                  <div className="border-b border-slate-200 pb-6 text-center space-y-2">
                    <span className="text-xs uppercase tracking-widest text-emerald-700 font-semibold block">
                      Department of Computer Science &amp; Engineering
                    </span>
                    <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                      {assessment?.courseId && !assessment.title?.startsWith(assessment.courseId)
                        ? `${assessment.courseId}: ${assessment.title}`
                        : assessment?.title}
                    </h2>
                    <div className="text-sm font-semibold text-slate-700 font-mono">
                      Examination Paper: Version {activeVersionLabel} ({activeVersionLabel === "A" ? "Main Session" : "Repeat / Alternative Session"})
                    </div>
                    <div className="flex justify-center items-center gap-6 text-xs text-slate-500 pt-2 font-mono">
                      <span>Total Marks: <strong className="text-slate-800">{targetMarks}</strong></span>
                      <span>Duration: <strong className="text-slate-800">{assessment?.durationMins} Minutes</strong></span>
                      <span>Questions: <strong className="text-slate-800">{activeVersionItems.length}</strong></span>
                    </div>
                  </div>

                  {/* Question Paper Body */}
                  <div className="space-y-6">
                    {filteredActiveVersionItems.map((item, qIdx) => (
                      <div
                        key={item.id}
                        className="p-5 rounded-xl bg-slate-50/70 border border-slate-200 space-y-4 hover:border-slate-300 transition"
                      >
                        {/* Question Top Meta */}
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <span className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold flex items-center justify-center font-mono">
                              Q{qIdx + 1}
                            </span>
                            <span className="text-slate-600 font-mono">[{item.marks} Marks]</span>
                            <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-[11px] font-mono font-medium">
                              {item.cloId}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[11px] border font-medium ${getBloomBadgeColor(item.bloom)}`}>
                              {item.bloom}
                            </span>
                          </div>

                          <span className="text-xs text-slate-500 font-mono">
                            Difficulty: {"★".repeat(item.difficulty)}{"☆".repeat(5 - item.difficulty)}
                          </span>
                        </div>

                        {/* Stem */}
                        <div className="text-sm text-slate-900 font-medium leading-relaxed">
                          {item.stem}
                        </div>

                        {/* MCQ Options */}
                        {item.qType === "mcq" && item.options && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                            {item.options.map((opt) => {
                              const isCorrect = opt.id === item.key && showAnswerKeys;

                              return (
                                <div
                                  key={opt.id}
                                  className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 transition ${
                                    isCorrect
                                      ? "bg-emerald-50 border-emerald-300 text-emerald-900 font-medium"
                                      : "bg-white border-slate-200 text-slate-800"
                                  }`}
                                >
                                  <span
                                    className={`w-5 h-5 rounded flex items-center justify-center font-bold text-xs shrink-0 ${
                                      isCorrect ? "bg-emerald-700 text-white" : "bg-slate-100 text-slate-600"
                                    }`}
                                  >
                                    {opt.id}
                                  </span>
                                  <span className="flex-1">{opt.text}</span>
                                  {isCorrect && (
                                    <span className="text-emerald-700 text-xs font-bold shrink-0">[Correct Key]</span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {/* Short Answer Rubric (if showAnswerKeys is on) */}
                        {item.qType === "short_answer" && showAnswerKeys && (
                          <div className="p-3.5 rounded-lg bg-emerald-50/60 border border-emerald-200 text-xs space-y-1.5">
                            <span className="text-emerald-800 font-semibold block">Model Answer &amp; Marking Rubric:</span>
                            <div className="text-slate-800 whitespace-pre-line font-mono text-[11px] leading-relaxed">
                              {item.key}
                            </div>
                          </div>
                        )}

                        {/* Citations */}
                        {item.sourceCitations && item.sourceCitations.length > 0 && (
                          <div className="pt-2 border-t border-slate-200 flex flex-wrap gap-1.5 items-center">
                            <span className="text-[11px] text-slate-500 font-medium">Grounded Source:</span>
                            {item.sourceCitations.map((cit, cIdx) => (
                              <span
                                key={cIdx}
                                className="text-[11px] px-2 py-0.5 rounded bg-white text-slate-700 border border-slate-200 truncate max-w-xs font-mono"
                                title={cit.snippet}
                              >
                                <FileText className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> {cit.title || cit.docId}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl p-12 text-center border border-slate-200/90 shadow-xs space-y-3">
                <Settings className="w-8 h-8 mx-auto text-slate-500" aria-hidden />
                <h4 className="text-base font-semibold text-slate-900">No versions assembled yet</h4>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Run CP-SAT assembly to build parallel versions that share no questions and carry the same marks per CLO and Bloom level.
                </p>
                <button
                  onClick={handleRunSolver}
                  disabled={runningSolver || isLocked}
                  title={lockedTitle}
                  className="mt-3 px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold cursor-pointer shadow-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Zap className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> Run CP-SAT Assembly
                </button>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 5: MODERATION & GOVERNANCE                                            */}
        {/* ========================================================================= */}
        {activeTab === "moderation" && (
          <div className="space-y-6">
            {/* Moderation Header & Status Banner */}
            <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                    Moderation and sign-off
                  </h3>
                  <p className="text-xs text-slate-500">
                    Live checks, the moderation agent&apos;s review, and the moderator&apos;s decision for {assessment?.courseId}.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {canRunAudit && (
                  <button
                    onClick={handleGenerateModeration}
                    disabled={generatingModeration}
                    className="px-4 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-semibold flex items-center gap-2 transition cursor-pointer shadow-xs disabled:opacity-50"
                  >
                    {generatingModeration ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
                        <span>Auditing Papers...</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-4 h-4" aria-hidden />
                        <span>{qaAudited ? "Re-Run QA Audit" : "Run QA Audit"}</span>
                      </>
                    )}
                  </button>
                  )}
                </div>
              </div>

              {/* Formal Approval Decision Banner */}
              <div
                className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                  moderationRecord?.decision === "approved"
                    ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                    : moderationRecord?.decision === "changes_requested"
                    ? "bg-amber-50 border-amber-200 text-amber-900"
                    : "bg-sky-50 border-sky-200 text-sky-900"
                }`}
              >
                <div className="flex items-center gap-3">
                  {moderationRecord?.decision === "approved" ? (
                    <CheckCircle2 className="w-6 h-6 shrink-0" aria-hidden />
                  ) : moderationRecord?.decision === "changes_requested" ? (
                    <AlertTriangle className="w-6 h-6 shrink-0" aria-hidden />
                  ) : (
                    <ClipboardList className="w-6 h-6 shrink-0" aria-hidden />
                  )}
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      {moderationRecord?.decision === "approved"
                        ? "Examination Package Formally Approved & Signed Off"
                        : moderationRecord?.decision === "changes_requested"
                        ? "Revision Requested by External Moderator"
                        : "Awaiting moderator sign-off"}
                    </h4>
                    <p className="text-xs text-slate-600">
                      {moderationRecord?.decision === "approved"
                        ? `Officially signed off by ${moderationRecord.decidedBy} on ${new Date(moderationRecord.decidedAt || "").toLocaleString()}. Locked for institutional printing & LMS deployment.`
                        : moderationRecord?.decision === "changes_requested"
                        ? `Changes requested by ${moderationRecord.decidedBy}. Review lecturer comments below.`
                        : readyForSignoff
                        ? "Every live check passes. Ready for the moderator's review and sign-off."
                        : signoffBlockers.length === 0 && !qaAudited
                        ? `Every live check passes, but the QA audit has never been run for this paper. ${canRunAudit ? "Run it" : "The moderator runs it"} before sign-off.`
                        : signoffBlockers.length === 0 && moderationStale
                        ? `Every live check passes, but the moderation pack is out of date. ${canRunAudit ? "Re-run" : "The moderator re-runs"} the QA audit before sign-off.`
                        : `Not ready for sign-off: ${signoffBlockers.length} of ${liveChecks.length} live checks are failing.`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <span className="font-mono text-slate-500">Current Persona:</span>
                  <span className="px-2.5 py-1 rounded-lg font-mono font-bold bg-white border border-slate-200 text-slate-800 shadow-xs">
                    {user.displayName} ({role})
                  </span>
                </div>
              </div>
            </div>

            {/* Moderation Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column (2 Cols): Executive Summary & AI Checklist */}
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <ListChecks className="w-4 h-4" aria-hidden /> Live checks
                    </h2>
                    <span className="text-xs font-mono text-slate-600">
                      {liveChecks.length - signoffBlockers.length} / {liveChecks.length} passing
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">Computed from this assessment&apos;s data each time the page loads.</p>
                  <ul className="divide-y divide-slate-100 border border-slate-200 rounded-lg">
                    {liveChecks.map((c) => (
                      <li key={c.title} className="px-3 py-2.5 flex items-center gap-3 text-sm">
                        {c.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" aria-label="Passing" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" aria-label="Failing" />
                        )}
                        <span className="flex-1 text-slate-900">{c.title}</span>
                        <span className={`text-xs font-mono ${c.passed ? "text-slate-600" : "text-amber-800"}`}>{c.note}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {!qaAudited && (
                  <div role="note" className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 flex gap-2.5">
                    <ShieldCheck className="w-4 h-4 mt-0.5 shrink-0 text-slate-500" aria-hidden />
                    <span>
                      QA audit never run: the moderation agent has not reviewed this paper yet.{" "}
                      {canRunAudit
                        ? "Click Run QA Audit to generate the checklist and executive summary."
                        : "The moderator runs it once the paper is submitted for moderation."}
                    </span>
                  </div>
                )}

                {moderationStale && (
                  <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 flex gap-2.5">
                    <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden />
                    <span>
                      Out of date: versions or reviewer flags changed after this moderation pack was generated, so the summary and
                      checklist below may not match the paper. {canRunAudit ? "Click Re-Run QA Audit to refresh them." : "The moderator re-runs the QA audit to refresh them."}
                    </span>
                  </div>
                )}

                {moderationRecord?.generatedBy === "fallback" && (
                  <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 flex gap-2.5">
                    <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden />
                    <span>
                      Generated offline: the LLM was unavailable when this pack was generated, so the summary and checklist below come
                      from rule-based checks, not the moderation agent&apos;s reading of the questions. Items marked Not assessed need
                      the agent. {canRunAudit ? "Re-Run QA Audit to try again." : "The moderator can re-run the QA audit."}
                    </span>
                  </div>
                )}

                {/* Executive Summary Card */}
                {moderationRecord?.executiveSummary && (
                  <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Landmark className="w-4 h-4" aria-hidden />
                        <h4 className="text-sm font-bold text-slate-900">
                          Executive summary
                        </h4>
                      </div>
                      <span
                        className={`text-[11px] px-2.5 py-0.5 rounded-full border font-medium ${
                          readyForSignoff
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : "bg-amber-50 text-amber-800 border-amber-200"
                        }`}
                      >
                        {readyForSignoff
                          ? "Ready for sign-off"
                          : `Not ready: ${signoffBlockers.length} ${signoffBlockers.length === 1 ? "check" : "checks"} failing`}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-200">
                      {moderationRecord.executiveSummary}
                    </p>
                  </div>
                )}

                {/* AI Verification Checklist */}
                {qaAudited && (
                <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ListChecks className="w-4 h-4" aria-hidden />
                      <h4 className="text-sm font-bold text-slate-900">
                        Moderation agent&apos;s checklist
                      </h4>
                    </div>
                    <span className="text-xs font-mono text-slate-500">
                      {moderationRecord?.checklist.filter((c) => c.passed).length || 0} of {moderationRecord?.checklist.length || 0} passed
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {moderationRecord?.checklist.map((chk) => {
                      const state = chk.passed ? "passed" : chk.notes?.startsWith("Not assessed") ? "unassessed" : "attention";
                      return (
                      <div
                        key={chk.id}
                        className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3 hover:border-slate-300 transition"
                      >
                        <span
                          className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                            state === "passed" ? "bg-emerald-600" : state === "unassessed" ? "bg-slate-400" : "bg-amber-500"
                          }`}
                          aria-hidden
                        />
                        <div className="flex-1 space-y-1">
                          <div className="flex items-start justify-between gap-3">
                            <span className="text-xs font-semibold text-slate-900">
                              {chk.title}
                            </span>
                            <span
                              className={`text-[11px] px-2 py-0.5 rounded font-semibold border whitespace-nowrap ${
                                state === "passed"
                                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                  : state === "unassessed"
                                  ? "bg-slate-100 text-slate-700 border-slate-200"
                                  : "bg-amber-50 text-amber-800 border-amber-200"
                              }`}
                            >
                              {state === "passed" ? "Passed" : state === "unassessed" ? "Not assessed" : "Needs attention"}
                            </span>
                          </div>
                          {chk.notes && (
                            <p className="text-xs text-slate-600 leading-relaxed">
                              {chk.notes}
                            </p>
                          )}
                        </div>
                      </div>
                      );
                    })}
                  </div>
                </div>
                )}

                {/* AI Constructive Feedback Comments */}
                {(moderationRecord?.aiComments.length || 0) > 0 && (
                <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Lightbulb className="w-4 h-4" aria-hidden />
                      <h4 className="text-sm font-bold text-slate-900">
                        AI Quality Assurance Feedback &amp; Item Observations
                      </h4>
                    </div>
                    <span className="text-xs text-slate-500">
                      {moderationRecord?.aiComments.length || 0} Specific Comments
                    </span>
                  </div>

                  <div className="space-y-3">
                    {moderationRecord?.aiComments.map((comment, cIdx) => (
                      <div
                        key={comment.id || cIdx}
                        className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-emerald-700 flex items-center gap-1.5">
                            <Bot className="w-4 h-4" aria-hidden /> {comment.author}
                          </span>
                          {comment.citedItemIds && comment.citedItemIds.length > 0 && (
                            <div className="flex items-center gap-1.5">
                              <span className="text-slate-500 text-[11px]">Cited:</span>
                              {comment.citedItemIds.map((iid) => (
                                <span
                                  key={iid}
                                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-white text-slate-700 border border-slate-200 font-semibold"
                                >
                                  {iid}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed">
                          {comment.text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
                )}
              </div>

              {/* Right Column (1 Col): Human Discussion & Sign-Off Actions */}
              <div className="space-y-6">
                {/* Formal Sign-Off Action Card */}
                <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-4">
                  <div className="flex items-center gap-2">
                    <PenLine className="w-4 h-4" aria-hidden />
                    <h4 className="text-sm font-bold text-slate-900">
                      Moderator decision
                    </h4>
                  </div>

                  {moderationRecord?.decision === "approved" ? (
                    <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-center space-y-2">
                      <ShieldCheck className="w-8 h-8 mx-auto text-slate-500" aria-hidden />
                      <h5 className="text-sm font-bold text-emerald-800">
                        Official Sign-Off Recorded
                      </h5>
                      <p className="text-xs text-slate-600">
                        Signed by <strong>{moderationRecord.decidedBy}</strong>
                        {moderationRecord.decidedAt ? ` on ${new Date(moderationRecord.decidedAt).toLocaleString()}` : ""}. The package is locked.
                      </p>
                    </div>
                  ) : canDecide && assessment?.status !== "in_moderation" ? (
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
                      {assessment?.status === "changes_requested" ? (
                        <>
                          <strong className="text-amber-800 block mb-1">Changes requested</strong>
                          The lecturer has been notified. You can decide again once they resubmit the paper.
                        </>
                      ) : (
                        <>
                          <strong className="text-slate-900 block mb-1">Not submitted yet</strong>
                          The lecturer has not submitted this paper for moderation.
                        </>
                      )}
                    </div>
                  ) : canDecide ? (
                    <div className="space-y-3">
                      <p className="text-xs text-slate-600">
                        As <strong>{user.displayName}</strong> ({decidingAs}), you possess the institutional authority to formally sign off or request changes on this assessment package.
                      </p>

                      <div>
                        <label htmlFor="decision-note" className="text-xs font-semibold text-slate-700 block mb-1">
                          Sign-off note (optional)
                        </label>
                        <textarea
                          id="decision-note"
                          value={decisionNote}
                          onChange={(e) => setDecisionNote(e.target.value)}
                          placeholder="e.g. Verified structural equivalence, distractor plausibility, and rubric alignment. Approved without reservation."
                          rows={3}
                          className="w-full text-xs bg-white border border-slate-200 rounded-lg p-3 text-slate-900 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                      </div>

                      <div className="flex flex-col gap-2 pt-1">
                        <button
                          onClick={() => setConfirmApproveOpen(true)}
                          disabled={submittingDecision || !readyForSignoff}
                          aria-describedby={!readyForSignoff ? "approve-blockers" : undefined}
                          className="w-full py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50 disabled:pointer-events-none"
                        >
                          <Check className="w-4 h-4" aria-hidden />
                          <span>Approve examination package…</span>
                        </button>
                        {!readyForSignoff && (
                          <div id="approve-blockers" className="text-xs text-slate-700 rounded-lg bg-slate-50 border border-slate-200 p-2.5">
                            <span className="font-semibold block mb-1">Approval unlocks when these pass:</span>
                            <ul className="list-disc pl-4 space-y-0.5">
                              {signoffBlockers.map((c) => (
                                <li key={c.title}>
                                  {c.title} <span className="text-slate-500">({c.note})</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <button
                          onClick={() => handleSubmitDecision("changes_requested")}
                          disabled={submittingDecision}
                          className="w-full py-2 rounded-lg bg-white hover:bg-slate-50 text-amber-700 border border-amber-300 text-xs font-medium transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                        >
                          <AlertTriangle className="w-4 h-4" aria-hidden />
                          <span>Request Revisions</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                      {/* The module's moderator (assigned per module by the admin) */}
                      <div className="flex items-start gap-2.5">
                        <Info className="w-4 h-4 text-sky-700 mt-0.5 shrink-0" aria-hidden />
                        <div className="min-w-0">
                          <h5 className="text-xs font-bold text-slate-900">
                            Moderator for <span className="font-mono">{assessment?.courseId}</span>
                          </h5>
                          {contacts?.moderator ? (
                            <p id="assigned-moderator" className="text-xs text-slate-600 mt-1 leading-relaxed break-words">
                              <strong className="text-slate-900">{contacts.moderator.displayName}</strong>
                              <br />
                              <a href={`mailto:${contacts.moderator.email}`} className="text-emerald-700 hover:underline">
                                {contacts.moderator.email}
                              </a>
                              {contacts.moderator.institution && (
                                <>
                                  <br />
                                  {contacts.moderator.institution}
                                </>
                              )}
                            </p>
                          ) : (
                            <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                              {contacts
                                ? `No moderator is assigned to module ${contacts.code} yet. Ask an administrator to assign one.`
                                : "Loading…"}
                            </p>
                          )}
                        </div>
                      </div>

                      {assessment?.status === "in_moderation" ? (
                        <p className="text-xs text-slate-700 rounded-lg bg-white border border-slate-200 p-2.5">
                          Submitted{assessment.submittedAt ? ` on ${new Date(assessment.submittedAt).toLocaleString()}` : ""}. Waiting for the moderator&apos;s decision; you&apos;ll get a notification.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {assessment?.status === "changes_requested" && (
                            <p className="text-xs text-amber-800 rounded-lg bg-amber-50 border border-amber-200 p-2.5">
                              The moderator requested changes. Address the comments below, then resubmit.
                            </p>
                          )}
                          <button
                            id="submit-for-moderation-btn"
                            onClick={handleSubmitForModeration}
                            disabled={
                              submittingForModeration ||
                              !contacts?.moderator ||
                              !SUBMITTABLE_STATUSES.includes(assessment?.status || "")
                            }
                            className="w-full py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50 disabled:pointer-events-none"
                          >
                            <Send className="w-4 h-4" aria-hidden />
                            <span>
                              {submittingForModeration
                                ? "Submitting…"
                                : assessment?.status === "changes_requested"
                                  ? "Resubmit for moderation"
                                  : "Submit for moderation"}
                            </span>
                          </button>
                          {!SUBMITTABLE_STATUSES.includes(assessment?.status || "") && (
                            <p className="text-[11px] text-slate-500">Assemble the paper versions first, then submit.</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Moderator Discussion & Feedback Thread */}
                <div className="bg-white rounded-xl p-5 border border-slate-200/90 shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="w-4 h-4" aria-hidden />
                      <h4 className="text-sm font-bold text-slate-900">
                        Moderation Discussion Thread
                      </h4>
                    </div>
                    <span className="text-xs text-slate-500 font-mono">
                      {moderationRecord?.humanComments.length || 0} Comments
                    </span>
                  </div>

                  {/* Comments list */}
                  <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                    {moderationRecord?.humanComments && moderationRecord.humanComments.length > 0 ? (
                      moderationRecord.humanComments.map((c, i) => (
                        <div
                          key={c.id || i}
                          className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5"
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-semibold text-slate-900">
                              {c.author}
                            </span>
                            <span className="px-1.5 py-0.5 rounded font-mono text-[11px] bg-white border border-slate-200 text-slate-600 uppercase">
                              {c.role}
                            </span>
                          </div>
                          <p className="text-xs text-slate-700 leading-relaxed">
                            {c.text}
                          </p>
                          {c.createdAt && (
                            <span className="text-[11px] text-slate-500 block text-right">
                              {new Date(c.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="p-4 rounded-lg bg-slate-50 text-center text-xs text-slate-500 border border-slate-200">
                        No human comments recorded yet. Add a lecturer note below.
                      </div>
                    )}
                  </div>

                  {/* Add comment input */}
                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    <textarea
                      aria-label="Add a moderation comment"
                      value={humanCommentText}
                      onChange={(e) => setHumanCommentText(e.target.value)}
                      placeholder="Add lecturer feedback, question note, or moderation observation..."
                      rows={2}
                      className="w-full text-xs bg-white border border-slate-200 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    />
                    <button
                      onClick={handleAddComment}
                      disabled={postingComment || !humanCommentText.trim()}
                      className="w-full py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold transition cursor-pointer shadow-xs disabled:opacity-50 disabled:pointer-events-none"
                    >
                      {postingComment ? "Submitting..." : "Post Comment"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 6: MULTI-FORMAT EXPORT & FINAL PACK                                   */}
        {/* ========================================================================= */}
        {activeTab === "export" && (
          <div className="space-y-6">
            {/* Export Header & Version Selector */}
            <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                    Assessment Export &amp; Distribution Package
                  </h3>
                  <p className="text-xs text-slate-500">
                    Generate officially formatted artifacts: ReportLab compiled PDF exam papers, confidential marking guides, Moodle XML quiz banks, and curriculum CLO alignment matrices.
                  </p>
                </div>

                {/* Draft vs official is driven by the moderation decision */}
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-3 py-1.5 rounded-lg font-bold font-mono border ${
                      assessment?.status === "approved"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                    }`}
                  >
                    {assessment?.status === "approved" ? "Approved: official watermark" : "Not approved yet: files carry a DRAFT watermark"}
                  </span>
                </div>
              </div>

              {/* Version Switcher Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-3 border-t border-slate-100">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-700">Target Paper Version:</span>
                  <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1 gap-1">
                    <button
                      onClick={() => setExportVersion("A")}
                      className={`px-3 py-1.5 rounded-md text-xs font-semibold transition cursor-pointer ${
                        exportVersion === "A"
                          ? "bg-emerald-700 text-white shadow-xs"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      Version A (Main Examination)
                    </button>
                    <button
                      onClick={() => setExportVersion("B")}
                      className={`px-3 py-1.5 rounded-md text-xs font-semibold transition cursor-pointer ${
                        exportVersion === "B"
                          ? "bg-emerald-700 text-white shadow-xs"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      Version B (Repeat Examination)
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                  <span>Questions in Version {exportVersion}: <strong className="text-slate-800">{versionItems[exportVersion]?.length ?? "—"}</strong></span>
                  <span>•</span>
                  <span>Total Marks: <strong className="text-slate-800">{targetMarks}</strong></span>
                </div>
              </div>
            </div>

            {/* 4 Multi-Format Export Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Card 1: Printable Examination Paper PDF */}
              <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-4 hover:border-slate-300 transition flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-10 h-10 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-bold flex items-center justify-center text-xl">
                        <FileText className="w-5 h-5" aria-hidden />
                      </span>
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">
                          Printable Examination Paper (PDF)
                        </h4>
                        <span className="text-[11px] text-slate-500 font-mono">
                          ReportLab 5.0 • A4 Document
                        </span>
                      </div>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200">
                      PDF
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    Official print-ready examination paper formatted for university sittings. Includes institutional header, candidate instructions, academic honor pledge, Section 1 MCQs, and Section 2 short-answer questions with working space and two-pass running footers.
                  </p>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[11px] space-y-1 text-slate-600 font-mono">
                    <div>• Format: Standard A4 Print-Ready PDF</div>
                    <div>• Content: Version {exportVersion} ({targetMarks} Marks, 120 Mins)</div>
                    <div>• Security: Two-pass page numbering &amp; watermarking</div>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={() => handleDownloadExport("pdf")}
                    disabled={downloadingFormat === "pdf"}
                    className="flex-1 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold transition flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                  >
                    {downloadingFormat === "pdf" ? (
                      <span>Generating PDF...</span>
                    ) : (
                      <>
                        <Download className="w-4 h-4" aria-hidden />
                        <span>Download Exam Paper PDF</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setExamPaperPreviewOpen(!examPaperPreviewOpen)}
                    className="px-3.5 py-2.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-semibold transition shadow-xs cursor-pointer"
                    title="Toggle On-Screen Preview"
                  >
                    <span><Eye className="inline w-3.5 h-3.5 -mt-0.5" aria-hidden /> Preview</span>
                  </button>
                </div>
              </div>

              {/* Card 2: Lecturer's Marking Guide & Rubric PDF */}
              <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-4 hover:border-slate-300 transition flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 font-bold flex items-center justify-center text-xl">
                        <ShieldCheck className="w-5 h-5" aria-hidden />
                      </span>
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">
                          Lecturer&apos;s Marking Guide &amp; Rubric (PDF)
                        </h4>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Confidential Lecturer Pack
                        </span>
                      </div>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded font-mono font-bold bg-amber-50 text-amber-700 border border-amber-200">
                      RESTRICTED
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    Confidential grading guide for academic markers. Contains complete MCQ answer key tables with pedagogical distractor rationales, and structured question model solutions with explicit point allocation rubrics and source citations.
                  </p>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[11px] space-y-1 text-slate-600 font-mono">
                    <div>• Section 1: MCQ Answer Key &amp; Rationale Matrix</div>
                    <div>• Section 2: Model Answers &amp; Itemized Point Schemes</div>
                    <div>• Classification: Strict Academic Lecturer Confidential</div>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => handleDownloadExport("keys")}
                    disabled={downloadingFormat === "keys"}
                    className="w-full py-2.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-semibold transition flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                  >
                    {downloadingFormat === "keys" ? (
                      <span>Generating Marking Guide...</span>
                    ) : (
                      <>
                        <Download className="w-4 h-4" aria-hidden />
                        <span>Download Marking Guide PDF</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Card 3: Moodle XML Quiz Bank */}
              <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-4 hover:border-slate-300 transition flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-10 h-10 rounded-lg bg-sky-50 border border-sky-200 text-sky-600 font-bold flex items-center justify-center text-xl">
                        <GraduationCap className="w-5 h-5" aria-hidden />
                      </span>
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">
                          Moodle XML Quiz Bank
                        </h4>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Moodle quiz import
                        </span>
                      </div>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded font-mono font-bold bg-sky-50 text-sky-700 border border-sky-200">
                      XML
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    Moodle XML with category paths, fractional scoring (100% correct, 0% per distractor), shuffle flags, distractor feedback, and CLO and Bloom tags.
                  </p>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[11px] space-y-1 text-slate-600 font-mono">
                    <div>• Type: Moodle &lt;quiz&gt; XML document</div>
                    <div>• Imports into: Moodle 3.x and 4.x</div>
                    <div>• Features: Distractor feedback, CLO tags, shuffle</div>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => handleDownloadExport("moodle_xml")}
                    disabled={downloadingFormat === "moodle_xml"}
                    className="w-full py-2.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-semibold transition flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                  >
                    {downloadingFormat === "moodle_xml" ? (
                      <span>Generating XML...</span>
                    ) : (
                      <>
                        <Download className="w-4 h-4" aria-hidden />
                        <span>Download Moodle XML Quiz Bank</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Card 4: CLO & Bloom Alignment Matrix CSV */}
              <div className="bg-white rounded-xl p-6 border border-slate-200/90 shadow-xs space-y-4 hover:border-slate-300 transition flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold flex items-center justify-center text-xl">
                        <BarChart3 className="w-5 h-5" aria-hidden />
                      </span>
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">
                          CLO Alignment Matrix (CSV)
                        </h4>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Curriculum mapping spreadsheet
                        </span>
                      </div>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      CSV
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    One row per question: its Course Learning Outcome (CLO), Bloom level, topic, difficulty, and source citations. Use it for curriculum and CLO coverage reviews.
                  </p>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[11px] space-y-1 text-slate-600 font-mono">
                    <div>• Columns: Q#, ItemID, CLO, Topic, Bloom, Diff, Citations</div>
                    <div>• Format: Standard RFC 4180 CSV</div>
                    <div>• Use: curriculum and CLO coverage review</div>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => handleDownloadExport("clo_csv")}
                    disabled={downloadingFormat === "clo_csv"}
                    className="w-full py-2.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-semibold transition flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                  >
                    {downloadingFormat === "clo_csv" ? (
                      <span>Generating CSV...</span>
                    ) : (
                      <>
                        <Download className="w-4 h-4" aria-hidden />
                        <span>Download Alignment Matrix CSV</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Optional On-Screen Exam Paper Preview Drawer */}
            {examPaperPreviewOpen && (
              <div className="bg-white rounded-xl p-6 sm:p-8 border border-slate-200/90 shadow-lg space-y-6">
                <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4" aria-hidden />
                    <h4 className="text-base font-bold text-slate-900">
                      Exam paper preview: Version {exportVersion}
                    </h4>
                  </div>
                  <button
                    onClick={() => setExamPaperPreviewOpen(false)}
                    className="text-xs text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 transition font-medium cursor-pointer"
                  >
                    Close preview
                  </button>
                </div>

                {/* Printable Formatted Paper Container */}
                <div className="bg-white text-slate-900 p-8 sm:p-12 rounded-xl shadow-md border border-slate-200 max-w-4xl mx-auto space-y-8 font-serif">
                  {/* Header */}
                  <div className="text-center space-y-1 border-b-2 border-slate-900 pb-4">
                    <h2 className="text-sm font-bold tracking-wider uppercase">
                      National University Examination Board
                    </h2>
                    <h3 className="text-xs font-medium text-slate-700">
                      Faculty of Computing &amp; Information Systems
                    </h3>
                    <h1 className="text-xl font-bold pt-2">
                      {assessment?.courseId}: {assessment?.title?.toUpperCase()}
                    </h1>
                    <div className="text-xs font-bold tracking-widest text-emerald-800 uppercase pt-1">
                      EXAMINATION PAPER — VERSION {exportVersion} ({exportVersion === "A" ? "MAIN SITTING" : "REPEAT SITTING"})
                    </div>
                  </div>

                  {/* Metadata Table */}
                  <div className="grid grid-cols-2 text-xs border border-slate-300 divide-x divide-slate-300 font-sans">
                    <div className="p-2 space-y-1">
                      <div><strong>Time Allowed:</strong> {assessment?.durationMins ? assessment.durationMins / 60 : 2} Hours ({assessment?.durationMins || 120} Minutes)</div>
                      <div><strong>Total Questions:</strong> {versionItems[exportVersion]?.length ?? "—"} Questions</div>
                    </div>
                    <div className="p-2 space-y-1">
                      <div><strong>Total Marks:</strong> {targetMarks} Marks</div>
                      <div><strong>Permitted Materials:</strong> None (Closed Book)</div>
                    </div>
                  </div>

                  {/* Instructions */}
                  <div className="bg-slate-50 p-4 rounded-lg text-xs space-y-1 font-sans border border-slate-200">
                    <h5 className="font-bold text-slate-900">INSTRUCTIONS TO CANDIDATES:</h5>
                    <ol className="list-decimal list-inside space-y-0.5 text-slate-700">
                      <li>
                        This examination consists of the following sections:{" "}
                        {QTYPE_ORDER.filter((qt) => (versionItems[exportVersion] || items).some((it) => it.qType === qt))
                          .map((qt, i) => `Section ${i + 1} (${QTYPE_LABEL[qt]})`)
                          .join(", ")}
                        .
                      </li>
                      <li>Answer <strong>ALL</strong> questions in every section.</li>
                      <li>For multiple choice, choose the single best answer and record it on the answer sheet.</li>
                      <li>For written sections, give concise, well-justified answers.</li>
                      <li><em>Honor Pledge: By commencing this exam, you certify that all work is solely your own.</em></li>
                    </ol>
                  </div>

                  {/* Section 1 Questions Preview */}
                  <div className="space-y-4 pt-4 border-t border-slate-200">
                    <h4 className="text-sm font-bold font-sans tracking-wide uppercase text-slate-900">
                      Section 1: Multiple Choice Questions [{(versionItems[exportVersion] || items).filter((it) => it.qType === "mcq").reduce((n, it) => n + it.marks, 0)} Marks]
                    </h4>

                    <div className="space-y-4 font-sans text-xs">
                      {(versionItems[exportVersion] || items)
                        .filter((it) => it.qType === "mcq")
                        .slice(0, 5)
                        .map((item, idx) => (
                          <div key={item.id} className="space-y-1.5 pb-3 border-b border-slate-200">
                            <div className="font-semibold text-slate-900">
                              Question {idx + 1} [{item.marks} Mark] <span className="text-slate-500 font-normal">({item.cloId} • {item.bloom})</span>
                            </div>
                            <p className="text-slate-800">{item.stem}</p>
                            {item.options && (
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 pt-1 pl-4">
                                {item.options.map((opt) => (
                                  <div key={opt.id} className="text-slate-700">
                                    <strong>[{opt.id}]</strong> {opt.text}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      <div className="text-center text-slate-500 italic text-[11px] pt-2">
                        [Showing first 5 of {(versionItems[exportVersion] || items).filter((it) => it.qType === "mcq").length} MCQ questions — Full paper compiled in PDF download]
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <NoticeToast notice={notice} onDismiss={() => setNotice(null)} />

      <ConfirmDialog
        open={confirmApproveOpen}
        title="Approve and lock this examination package?"
        confirmLabel="Approve and lock"
        busy={submittingDecision}
        onCancel={() => setConfirmApproveOpen(false)}
        onConfirm={async () => {
          await handleSubmitDecision("approved");
          setConfirmApproveOpen(false);
        }}
      >
        <p>Approval is recorded against your name and cannot be undone from this screen. It locks:</p>
        <ul className="rounded-lg border border-slate-200 divide-y divide-slate-100 font-mono text-xs">
          {versions.map((v) => (
            <li key={v.id} className="px-3 py-2 flex justify-between">
              <span>Version {v.label}</span>
              <span>
                {v.itemIds.length} questions · {equivalenceReport?.perVersion?.[v.label]?.totalMarks ?? "—"} marks
              </span>
            </li>
          ))}
        </ul>
        <p className="text-xs text-slate-500">
          Signing as {user.displayName} ({decidingAs}).{decisionNote.trim() ? " Your note will be attached." : ""}
        </p>
      </ConfirmDialog>

      {/* Slide-Out Agent Trace Drawer */}
      <AgentTraceDrawer
        runId={assessment?.runId || null}
        isOpen={isTraceOpen}
        onClose={() => setIsTraceOpen(false)}
      />

      {/* Keyboard Shortcuts Modal */}
      {showShortcuts && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="shortcuts-title"
          onClick={() => setShowShortcuts(false)}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs cursor-pointer"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4 cursor-default"
          >
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-emerald-700" aria-hidden />
                <h3 id="shortcuts-title" className="text-sm font-bold text-slate-900">
                  Keyboard Shortcuts
                </h3>
              </div>
              <button
                onClick={() => setShowShortcuts(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md cursor-pointer"
                aria-label="Close shortcuts dialog"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="text-xs space-y-2.5 text-slate-700">
              <div className="flex justify-between items-center py-1 border-b border-slate-100">
                <span>Cycle workflow tabs</span>
                <div className="flex gap-1 font-mono">
                  <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px]">[</kbd>
                  <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px]">]</kbd>
                </div>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-100">
                <span>Jump to tab (1–6)</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] font-mono">Alt + 1..6</kbd>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-100">
                <span>Toggle Agent Trace drawer</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] font-mono">Alt + T</kbd>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-100">
                <span>Toggle paper preview (Export/Solver)</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] font-mono">Alt + P</kbd>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-100">
                <span>Close modal / drawer</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] font-mono">Esc</kbd>
              </div>
              <div className="flex justify-between items-center py-1">
                <span>Toggle shortcuts dialog</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] font-mono">?</kbd>
              </div>
            </div>
            <div className="pt-2 text-right">
              <button
                onClick={() => setShowShortcuts(false)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AssessmentWorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-600">
          <Loader2 className="w-5 h-5 mr-2 animate-spin" aria-hidden /> Loading Assessment...
        </div>
      }
    >
      <AssessmentWorkspaceContent />
    </Suspense>
  );
}
