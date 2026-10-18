from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
import re
import time
import uuid
from datetime import datetime, timezone


def generate_id() -> str:
    return str(uuid.uuid4())


def current_time_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------------------
# Users
# ------------------------------------------------------------------------------
UserRole = Literal["admin", "lecturer", "moderator", "system"]

# Canonical order; the first role a user holds is their primary `role`.
ROLE_ORDER = ("admin", "lecturer", "moderator", "system")


def normalize_roles(roles) -> List[str]:
    """De-duplicates and orders roles, dropping unknown values."""
    held = set(roles or [])
    return [r for r in ROLE_ORDER if r in held]


UserTitle = Literal["Dr.", "Prof.", "Mr.", "Mrs.", "Ms.", "Miss"]
USER_TITLES = ("Dr.", "Prof.", "Mr.", "Mrs.", "Ms.", "Miss")


def split_title(display_name: str) -> tuple:
    """Splits a leading title off a display name: "Dr. Amali Perera" -> ("Dr.", "Amali Perera")."""
    name = (display_name or "").strip()
    first, _, rest = name.partition(" ")
    for title in USER_TITLES:
        if rest and first.lower().rstrip(".") == title.lower().rstrip("."):
            return title, rest.strip()
    return None, name


def with_title(title: Optional[str], name: str) -> str:
    """The display name shown everywhere: the title (if any) followed by the bare name."""
    name = split_title(name)[1]
    return f"{title} {name}" if title else name


def split_name(name: str) -> tuple:
    """Splits a bare name into (first, middle, last): "Amali Nadeesha Perera" -> ("Amali", "Nadeesha", "Perera")."""
    parts = (name or "").split()
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def join_name(*parts: Optional[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def name_parts(doc: dict) -> tuple:
    """(title, first, middle, last) for a users record; older records only have the combined displayName."""
    title, bare = split_title(doc.get("displayName", ""))
    title = doc.get("title") or title
    if doc.get("firstName") or doc.get("lastName"):
        return title, doc.get("firstName") or "", doc.get("middleName") or "", doc.get("lastName") or ""
    # Drop a trailing label such as "(Lecturer)": it is not part of the name.
    return (title, *split_name(re.sub(r"\s*\(.*\)\s*$", "", bare)))


def roles_of(doc: Optional[dict]) -> List[str]:
    """The roles on a stored users/{uid} record; older records only have a single `role`."""
    if not doc:
        return []
    return normalize_roles(doc.get("roles") or ([doc["role"]] if doc.get("role") else []))


class User(BaseModel):
    uid: str
    email: str
    # The full name as shown, including the title ("Dr. Amali Perera").
    displayName: str
    # Set separately by an administrator; displayName is "<title> <first> <middle> <last>".
    title: Optional[UserTitle] = None
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    # Primary role (the first of `roles`), kept for older records, comments and analytics.
    role: UserRole = "lecturer"
    # Everything the user may do: a lecturer can also moderate other modules.
    roles: List[UserRole] = Field(default_factory=list)
    institution: str = "AssessCraft University"
    disabled: bool = False
    createdAt: str = Field(default_factory=current_time_iso)
    updatedAt: str = Field(default_factory=current_time_iso)

    @model_validator(mode="after")
    def _sync_roles(self):
        self.roles = normalize_roles(self.roles) or [self.role]
        self.role = self.roles[0]
        return self

    def has_role(self, *names: str) -> bool:
        return any(r in self.roles for r in names)


AdminAssignableRole = Literal["admin", "lecturer", "moderator"]


class AdminUserCreate(BaseModel):
    email: str
    title: Optional[UserTitle] = None
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    # Older clients send the whole name here instead of the parts; it is split on spaces.
    displayName: Optional[str] = None
    role: AdminAssignableRole = "lecturer"
    # Takes precedence over `role` when given.
    roles: Optional[List[AdminAssignableRole]] = None
    password: str = Field(min_length=6)
    institution: Optional[str] = None

    def resolved_roles(self) -> List[str]:
        return normalize_roles(self.roles) or [self.role]

    def resolved_name(self) -> tuple:
        """(first, middle, last), from the parts when given, else split from displayName."""
        if self.firstName or self.lastName:
            return (self.firstName or "").strip(), (self.middleName or "").strip(), (self.lastName or "").strip()
        return split_name(split_title(self.displayName or "")[1])


class AdminUserUpdate(BaseModel):
    # "" removes the title (or the middle name).
    title: Optional[Literal["Dr.", "Prof.", "Mr.", "Mrs.", "Ms.", "Miss", ""]] = None
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    # Older clients send the whole name (without title) here; it is split on spaces.
    displayName: Optional[str] = None
    role: Optional[AdminAssignableRole] = None
    # Replaces all of the user's roles; takes precedence over `role`.
    roles: Optional[List[AdminAssignableRole]] = None
    institution: Optional[str] = None
    disabled: Optional[bool] = None
    # Sets a new sign-in password (Firebase accounts only).
    password: Optional[str] = Field(default=None, min_length=6)


class UserSummary(BaseModel):
    """The public contact details a lecturer sees for their assigned moderator (and vice versa)."""
    uid: str
    email: str
    displayName: str
    role: UserRole
    roles: List[UserRole] = Field(default_factory=list)
    institution: Optional[str] = None


# ------------------------------------------------------------------------------
# Course, CLO, Topic
# ------------------------------------------------------------------------------
BloomLevel = Literal["remember", "understand", "apply", "analyse", "evaluate", "create"]


class CLO(BaseModel):
    id: str  # e.g., "CLO1"
    text: str
    bloomLevel: Optional[BloomLevel] = "understand"


class Topic(BaseModel):
    id: str
    name: str
    cloIds: List[str] = Field(default_factory=list)


class Course(BaseModel):
    id: str
    code: str  # e.g., "CS2040"
    title: str  # e.g., "Database Systems"
    ownerUid: str
    # The moderator who reviews this module's papers. Set per module, so one lecturer's modules
    # can each have a different moderator.
    moderatorUid: Optional[str] = None
    clos: List[CLO] = Field(default_factory=list)
    topics: List[Topic] = Field(default_factory=list)
    confirmed: bool = False
    createdAt: str = Field(default_factory=current_time_iso)
    updatedAt: str = Field(default_factory=current_time_iso)


class CourseCreate(BaseModel):
    code: str
    title: str
    # Admin only: the lecturer who owns the module. Lecturers own what they create; an admin's
    # module stays unassigned ("") until an owner is chosen.
    ownerUid: Optional[str] = None
    # Admin only: the module's moderator.
    moderatorUid: Optional[str] = None
    clos: Optional[List[CLO]] = None
    topics: Optional[List[Topic]] = None


class CourseUpdate(BaseModel):
    """Admin edit of a module. "" clears the owner or moderator."""
    title: Optional[str] = None
    ownerUid: Optional[str] = None
    moderatorUid: Optional[str] = None


class CourseOutcomesUpdate(BaseModel):
    clos: List[CLO]
    topics: List[Topic]
    confirmed: bool = True


# ------------------------------------------------------------------------------
# Documents & Past Items
# ------------------------------------------------------------------------------
# "qa_manual" is no longer offered for upload but stays valid for documents already stored.
DocKind = Literal["syllabus", "notes", "slides", "past_paper", "model_paper", "rubric", "qa_manual"]
DocStatus = Literal["pending", "processing", "indexed", "failed"]


class Document(BaseModel):
    id: str
    courseId: str
    title: str
    kind: DocKind
    year: Optional[int] = None
    gcsUri: Optional[str] = None
    textGcsUri: Optional[str] = None
    status: DocStatus = "indexed"
    searchDocId: Optional[str] = None
    contentSnippet: Optional[str] = None
    createdAt: str = Field(default_factory=current_time_iso)
    updatedAt: str = Field(default_factory=current_time_iso)


class PastItem(BaseModel):
    id: str
    courseId: str
    docId: str
    year: int
    text: str
    embedding: Optional[List[float]] = None


# ------------------------------------------------------------------------------
# Assessment
# ------------------------------------------------------------------------------
AssessmentStatus = Literal[
    "draft",
    "blueprint_ready",
    "pool_ready",
    "reviewed",
    "assembled",
    "in_moderation",
    "changes_requested",
    "approved"
]

QuestionType = Literal["mcq", "short_answer", "essay"]


class TypeConfig(BaseModel):
    """Lecturer's per-question-type targets: count items worth `marks` in total, ~timeMins suggested."""
    qType: QuestionType
    count: int = Field(ge=1, le=50)
    marks: int = Field(ge=1, le=1000)
    timeMins: int = Field(0, ge=0, le=600)


class Assessment(BaseModel):
    id: str
    courseId: str
    title: str
    request: str = ""
    totalMarks: int = 100
    durationMins: int = 120
    numVersions: int = 2
    qTypes: List[QuestionType] = Field(default_factory=lambda: ["mcq", "short_answer"])
    typeConfig: Optional[List[TypeConfig]] = None
    status: AssessmentStatus = "draft"
    runId: Optional[str] = None
    createdAt: str = Field(default_factory=current_time_iso)
    updatedAt: str = Field(default_factory=current_time_iso)

    @field_validator("qTypes", mode="before")
    @classmethod
    def normalize_qtypes(cls, v):
        if not v:
            return ["mcq", "short_answer"]
        valid = {"mcq", "short_answer", "essay"}
        result = []
        for t in v:
            if t in valid:
                result.append(t)
            elif str(t).lower() in ("mcq", "multiple_choice"):
                result.append("mcq")
            elif str(t).lower() in ("short_answer", "shortanswer", "saq"):
                result.append("short_answer")
            elif str(t).lower() in ("essay", "long_answer"):
                result.append("essay")
        return result or ["mcq", "short_answer"]
    createdBy: str = "lecturer@demo"
    createdByUid: Optional[str] = None
    # Set when the lecturer submits the paper for moderation (copied from the module's moderator).
    moderatorUid: Optional[str] = None
    submittedAt: Optional[str] = None


class AssessmentCreate(BaseModel):
    courseId: str
    title: Optional[str] = None
    # Optional topic focus; counts and marks come from typeConfig.
    request: str = ""
    totalMarks: int = Field(100, ge=1, le=1000)
    durationMins: int = 120
    numVersions: int = Field(2, ge=1, le=2)
    qTypes: Optional[List[QuestionType]] = None
    typeConfig: Optional[List[TypeConfig]] = None

    @model_validator(mode="after")
    def derive_from_type_config(self):
        # typeConfig is the source of truth: totals and qTypes are derived from it.
        if not self.typeConfig:
            return self
        types = [t.qType for t in self.typeConfig]
        if len(set(types)) != len(types):
            raise ValueError("Each question type may appear only once in typeConfig.")
        for t in self.typeConfig:
            if t.marks % t.count:
                raise ValueError(f"{t.qType}: {t.marks} marks cannot be split evenly across {t.count} questions.")
        self.totalMarks = sum(t.marks for t in self.typeConfig)
        if self.totalMarks > 1000:
            raise ValueError("Total marks may not exceed 1000.")
        self.durationMins = sum(t.timeMins for t in self.typeConfig) or self.durationMins
        self.qTypes = types
        return self


# ------------------------------------------------------------------------------
# Blueprint
# ------------------------------------------------------------------------------
class BlueprintCell(BaseModel):
    cloId: str
    topicId: str
    bloom: BloomLevel
    qType: QuestionType
    # Bounded: the item writer drafts up to 2.5x count candidates, so an unbounded count is an unbounded LLM bill.
    count: int = Field(ge=0, le=50)
    marksEach: int = Field(ge=1, le=100)


class Blueprint(BaseModel):
    assessmentId: str
    cells: List[BlueprintCell] = Field(default_factory=list)
    totals: Dict[str, Any] = Field(default_factory=dict)
    valid: bool = False
    violations: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    updatedAt: str = Field(default_factory=current_time_iso)


# ------------------------------------------------------------------------------
# Item & Options & Source Citations
# ------------------------------------------------------------------------------
ItemStatus = Literal["candidate", "accepted", "rejected"]


class Option(BaseModel):
    id: str  # "A", "B", "C", "D"
    text: str


class SourceCitation(BaseModel):
    docId: str
    snippet: str
    uri: Optional[str] = None
    title: Optional[str] = None


class Item(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    assessmentId: str
    stem: str
    options: Optional[List[Option]] = None
    key: str  # e.g., "A" for MCQ, or concise rubric for short answer
    rationale: str
    qType: QuestionType = "mcq"
    marks: int = 2
    cloId: str
    topicId: str
    bloom: BloomLevel = "understand"
    bloomConfirmed: bool = False
    difficulty: int = 3  # 1 to 5
    difficultySource: Literal["ai", "lecturer"] = "ai"
    sourceCitations: List[SourceCitation] = Field(default_factory=list)
    status: ItemStatus = "candidate"
    embedding: Optional[List[float]] = None
    promptVersion: Optional[str] = "v1.0"
    createdAt: str = Field(default_factory=current_time_iso)
    updatedAt: str = Field(default_factory=current_time_iso)


class ItemUpdate(BaseModel):
    stem: Optional[str] = None
    options: Optional[List[Option]] = None
    key: Optional[str] = None
    rationale: Optional[str] = None
    marks: Optional[int] = None
    cloId: Optional[str] = None
    topicId: Optional[str] = None
    bloom: Optional[BloomLevel] = None
    bloomConfirmed: Optional[bool] = None
    difficulty: Optional[int] = None
    difficultySource: Optional[Literal["ai", "lecturer"]] = None
    status: Optional[ItemStatus] = None


# ------------------------------------------------------------------------------
# Flags
# ------------------------------------------------------------------------------
FlagType = Literal[
    "key_mismatch",
    "ambiguous",
    "item_flaw",
    "duplicate_past",
    "duplicate_pool",
    "misaligned_clo",
    "bloom_doubt"
]

FlagSeverity = Literal["high", "medium", "low"]
FlagResolution = Literal["accepted", "dismissed", "edited"]


class Flag(BaseModel):
    id: str
    itemId: str
    assessmentId: str
    type: FlagType
    severity: FlagSeverity = "medium"
    detail: str
    evidence: str
    resolution: Optional[FlagResolution] = None
    resolvedBy: Optional[str] = None
    createdAt: str = Field(default_factory=current_time_iso)
    updatedAt: str = Field(default_factory=current_time_iso)


class FlagResolutionRequest(BaseModel):
    resolution: FlagResolution
    detail: Optional[str] = None


# ------------------------------------------------------------------------------
# Versions & Solver
# ------------------------------------------------------------------------------
class PaperVersion(BaseModel):
    id: str
    assessmentId: str
    label: str  # "A", "B", "C"
    itemIds: List[str] = Field(default_factory=list)
    solverStats: Dict[str, Any] = Field(default_factory=dict)
    createdAt: str = Field(default_factory=current_time_iso)


class EquivalenceReport(BaseModel):
    assessmentId: str
    perVersion: Dict[str, Any] = Field(default_factory=dict)
    deviations: Dict[str, Any] = Field(default_factory=dict)
    guaranteed: List[str] = Field(default_factory=list)
    estimated: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(
        default_factory=lambda: [
            "Matching blueprints do not prove equal difficulty; empirical comparability requires student response data."
        ]
    )
    solverStatus: str = "OPTIMAL"
    createdAt: str = Field(default_factory=current_time_iso)


# ------------------------------------------------------------------------------
# Moderation
# ------------------------------------------------------------------------------
class ModerationItem(BaseModel):
    id: str
    title: str
    passed: bool
    notes: Optional[str] = None


class Comment(BaseModel):
    id: str = Field(default_factory=generate_id)
    author: str  # "AI Moderator" or user email
    role: str
    text: str
    citedItemIds: List[str] = Field(default_factory=list)
    createdAt: str = Field(default_factory=current_time_iso)


class ModerationRecord(BaseModel):
    assessmentId: str
    checklist: List[ModerationItem] = Field(default_factory=list)
    aiComments: List[Comment] = Field(default_factory=list)
    humanComments: List[Comment] = Field(default_factory=list)
    executiveSummary: Optional[str] = None
    decision: Optional[Literal["approved", "changes_requested"]] = None
    decidedBy: Optional[str] = None
    decidedAt: Optional[str] = None
    updatedAt: str = Field(default_factory=current_time_iso)
    # "fallback" when the LLM was unavailable and the checklist/summary are deterministic placeholders.
    generatedBy: Literal["agent", "fallback"] = "agent"
    # Fingerprint of the versions and open flags the pack was generated from (see moderation.inputs_key).
    inputsKey: Optional[str] = None
    # Computed on read, never stored: true when versions or flags changed after generation.
    stale: bool = False


class ModerationDecisionRequest(BaseModel):
    decision: Literal["approved", "changes_requested"]
    comment: Optional[str] = None


# ------------------------------------------------------------------------------
# Agent Run Tracing
# ------------------------------------------------------------------------------
class RunStep(BaseModel):
    stepId: str = Field(default_factory=generate_id)
    agent: str  # e.g., "DocIntel", "Blueprint", "ItemWriter", "Reviewer", "Moderation"
    tool: Optional[str] = None
    input_summary: str
    output_summary: str
    sources: List[str] = Field(default_factory=list)
    startedAt: str = Field(default_factory=current_time_iso)
    endedAt: Optional[str] = None
    status: Literal["running", "completed", "failed"] = "completed"
    durationMs: Optional[int] = None


class RunTrace(BaseModel):
    id: str
    assessmentId: Optional[str] = None
    courseId: Optional[str] = None
    workflow: str = "assessment_generation"
    status: Literal["running", "completed", "failed"] = "running"
    steps: List[RunStep] = Field(default_factory=list)
    createdAt: str = Field(default_factory=current_time_iso)
    updatedAt: str = Field(default_factory=current_time_iso)


# ------------------------------------------------------------------------------
# Audit Log
# ------------------------------------------------------------------------------
class AuditEntry(BaseModel):
    id: str = Field(default_factory=generate_id)
    actorUid: str
    action: str
    entity: str
    entityId: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    at: str = Field(default_factory=current_time_iso)


# ------------------------------------------------------------------------------
# Notifications (in-app)
# ------------------------------------------------------------------------------
NotificationType = Literal[
    "submitted_for_moderation",
    "moderation_approved",
    "moderation_changes_requested",
    "moderator_assigned",
    "module_assigned",
]


class Notification(BaseModel):
    id: str = Field(default_factory=generate_id)
    recipientUid: str
    type: NotificationType
    title: str
    message: str
    assessmentId: Optional[str] = None
    actorName: Optional[str] = None
    read: bool = False
    # Millisecond precision so notifications created in the same second still sort newest-first.
    createdAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )
