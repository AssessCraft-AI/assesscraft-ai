# Build Prompt: AssessCraft AI Prototype on Google Cloud

> **How to use:** paste everything below the line into an AI coding agent (Claude Code, Gemini CLI, Antigravity, Cursor and similar). Fill in the values in `<ANGLE_BRACKETS>` first. The prompt is designed to be run milestone by milestone: ask the agent to complete one milestone, review it, then continue.

---

## ROLE

You are a senior full-stack and AI engineer. Build, test and deploy a **working prototype** of **AssessCraft AI**, an agentic copilot for academic assessment work, on **Google Cloud**. It is an entry for the Google Cloud AI Builder Cup 2026, *Future of Work & Enterprise Productivity* theme.

Judging weights are:

- **Technical Merit & GenAI Implementation: 40%**
- Problem Alignment & Impact: 25%
- Innovation: 25%
- UX: 10%

Prioritise, in this order:
1. A reliable end-to-end demo.
2. Visible, genuine use of Gemini and agents.
3. Clean UX.

There are about **7 days** to build. Do not over-engineer.

## PROJECT VALUES

```
GCP_PROJECT_ID      = <your-project-id>
GCP_REGION          = asia-southeast1        # or us-central1 if a service is unavailable in-region
GEMINI_MODEL        = gemini-2.5-flash       # make configurable; use gemini-2.5-pro for the Reviewer if quality needs it
VERTEX_SEARCH_LOC   = global
APP_NAME            = assesscraft
```

Before using any model ID, ADK API or Vertex AI Search API, **check the current official docs**. Model names and SDK signatures change. If something is unavailable in the chosen region, use the nearest supported region and record why in `docs/DECISIONS.md`.

---

## 1. WHAT THE PRODUCT DOES

**Accounts are admin-managed.** There is no self sign-up. An administrator creates every account (lecturer, moderator, QA officer, admin), sets its role, and assigns each lecturer the moderator who will review that lecturer's papers. The lecturer is the paper's examiner (author). Both sides see each other's contact details once assigned.

A lecturer types a request such as: *"Create a main paper and a repeat paper for CS2040 Database Systems, 100 marks, 2 hours, MCQ + short answer."* Specialised agents then do the following, with the lecturer approving at checkpoints:

1. **Retrieve and understand.** Parse the course syllabus, CLOs and past papers. Extract CLOs and topics. The lecturer confirms them.
2. **Blueprint.** Propose a marks matrix (CLO × Bloom's level × topic × question type). The lecturer edits it, and deterministic validation enforces totals.
3. **Draft.** Generate a candidate item pool (about 2.5× the items needed). Ground each item in a cited source passage. Tag each with CLO, topic, Bloom's level, question type, marks and a difficulty estimate.
4. **Review.** For each item:
   - solve it independently without seeing the key, and flag any mismatch;
   - check consistency across several solutions;
   - detect item-writing flaws;
   - find near-duplicates against past papers and within the pool.

   The lecturer accepts, edits or rejects each flag.
5. **Assemble.** An OR-Tools CP-SAT solver builds 2–3 versions with an **exact** blueprint match and a minimal difficulty gap, with no near-duplicates in the same version and no item reused across versions.
6. **Moderate.** When the paper is assembled, the lecturer clicks **Submit for moderation**. The paper goes to the lecturer's assigned moderator, who gets an in-app notification. A moderation pack is prepared: the versions, the keys, an equivalence report, the flags and decisions, and drafted moderator comments. The moderator comments, then either approves (the package locks for export) or requests changes. The lecturer is notified of either outcome and can revise and resubmit, which reopens the decision.
7. **Export.** Approved papers and answer keys as PDF (with per-version watermark), question banks as Moodle XML, and a CLO alignment matrix as CSV.
8. **Knowledge assistant.** A chat panel answers questions over the institution's documents, with citations. Examples: "Was a question on SQL outer joins used in the last 3 years?", "What does the QA manual require for repeat papers?"
9. **Productivity analytics.** Log time-on-task, flags raised and accepted, and edits to BigQuery, and show a small dashboard.

**Out of scope:** online exam delivery, student logins, essay/code marking, LTI integration, multilingual generation.

---

## 2. ARCHITECTURE

```
React frontend (Vite, Cloud Run) ──HTTPS──▶ Spring Boot backend (Cloud Run)
                                            │
                                            ├── ADK multi-agent system (google-adk, Python sidecar or REST bridge)
                                            │      Orchestrator → DocIntel, Blueprint, ItemWriter,
                                            │                     Reviewer, Moderation agents
                                            │      Tools: search_knowledge_base, parse_document,
                                            │             validate_blueprint, assemble_versions,
                                            │             find_similar_items, save_*/load_* (Firestore)
                                            ├── Gemini on Vertex AI (Vertex AI Java SDK / REST)
                                            ├── Vertex AI Search data store (course docs + past papers)
                                            ├── Document AI (OCR processor for scanned PDFs)
                                            ├── OR-Tools CP-SAT (in-process via or-tools Java library)
                                            ├── Firestore (app data + audit trail + agent run traces)
                                            ├── Cloud Storage (uploads, exports)
                                            └── BigQuery (productivity + quality events)
Auth: Firebase Authentication (email/password + Google), roles stored in Firestore
```

**Tech stack details:**
- **Backend:** Java 17+, Spring Boot 3.2.5, Maven, Jackson for JSON, Jakarta Validation, Spring Web.
- **Frontend:** React 19, Vite 6, vanilla CSS (custom design system), Lucide React icons, Recharts for charts.
- **State (prototype):** In-memory `DataStoreService` using `ConcurrentHashMap` (replaces Firestore for the prototype). Swap to Firestore for production.

**Agent hosting decision:**
- Build agents with **ADK** (Python) and run them as a **sidecar service** or invoke them via REST from the Spring Boot backend.
- In Milestone 7, **also deploy the orchestrator to Vertex AI Agent Engine** and add a backend config flag `agent.runtime=local|agent_engine`.
- If Agent Engine deployment blocks progress, keep the local runtime and document it. The demo must not depend on a fragile path.

**Determinism rule:** never let an LLM do arithmetic or constraint satisfaction. Totals, blueprint validation, assembly and statistics are Java code. LLMs produce structured JSON validated by Jackson deserialization and Jakarta Bean Validation. Retry up to 2 times on validation failure, then surface an error.

---

## 3. REPOSITORY STRUCTURE

The project uses **two separate repositories**:

### 3.1 Backend — `assesscraft_backend/`

```
assesscraft_backend/
├── README.md                            # setup, run locally, deploy, demo script
├── docs/DECISIONS.md                    # architecture decisions and deviations
├── docs/DEMO_SCRIPT.md
├── infra/
│   ├── setup.sh                         # enable APIs, create resources, service accounts, IAM
│   ├── deploy_backend.sh
│   ├── bigquery_schema.json
│   └── firestore.indexes.json
├── pom.xml                              # spring-boot-starter-web, jackson-databind,
│                                        # jakarta.validation, spring-boot-starter-test,
│                                        # google-cloud-firestore, google-cloud-storage,
│                                        # google-cloud-discoveryengine, google-cloud-documentai,
│                                        # google-cloud-bigquery, com.google.ortools:ortools-java
├── Dockerfile
├── src/main/java/com/assesscraft/
│   ├── AssessCraftBackendApplication.java   # Spring Boot entry point
│   ├── config/
│   │   └── WebConfig.java                   # CORS configuration, request filters
│   ├── model/                               # POJOs with Jackson annotations (see §4)
│   │   ├── User.java
│   │   ├── Course.java, CourseCreate.java, CourseOutcomesUpdate.java
│   │   ├── CLO.java, Topic.java
│   │   ├── Document.java
│   │   ├── Assessment.java, AssessmentCreate.java
│   │   ├── Blueprint.java, BlueprintCell.java
│   │   ├── Item.java, ItemUpdate.java, Option.java, SourceCitation.java
│   │   ├── Flag.java, FlagResolutionRequest.java
│   │   ├── PaperVersion.java, EquivalenceReport.java
│   │   ├── ModerationRecord.java, ModerationItem.java, Comment.java
│   │   ├── ModerationDecisionRequest.java
│   │   ├── RunTrace.java, RunStep.java
│   │   ├── PastItem.java
│   │   └── AnalyticsSummary.java
│   ├── controller/                          # REST controllers (see §8)
│   │   ├── CourseController.java            # /api/courses/**
│   │   ├── AssessmentController.java        # /api/assessments/**
│   │   ├── BlueprintController.java         # /api/assessments/{id}/blueprint
│   │   ├── ItemController.java             # /api/assessments/{id}/items, /api/items/{id}
│   │   ├── FlagController.java             # /api/assessments/{id}/flags, /api/flags/{id}
│   │   ├── VersionController.java          # /api/assessments/{id}/versions
│   │   ├── ModerationController.java       # /api/assessments/{id}/moderation
│   │   ├── ExportController.java           # /api/assessments/{id}/export
│   │   ├── AssistantController.java        # /api/courses/{id}/assistant
│   │   ├── RunController.java              # /api/runs/{id}
│   │   ├── AnalyticsController.java        # /api/analytics/summary
│   │   ├── MeController.java              # /api/me
│   │   └── SystemController.java           # /api/system/health
│   └── service/
│       └── DataStoreService.java            # In-memory data store (ConcurrentHashMap),
│                                            # seeded with demo data (CS2040 course,
│                                            # assessment pipeline states). Swap to
│                                            # Firestore repositories for production.
├── src/main/resources/
│   └── application.properties               # server.port, CORS origins, feature flags
├── src/test/java/com/assesscraft/          # JUnit 5 tests: solver, blueprint rules,
│                                            # exporters, API smoke tests
└── seed/                                    # sample course data (see §9)
```

### 3.2 Frontend — `assesscraft_frontend/`

```
assesscraft_frontend/
├── README.md
├── package.json                         # react, react-dom, vite, @vitejs/plugin-react,
│                                        # lucide-react, recharts, firebase
├── vite.config.js
├── Dockerfile
├── index.html
├── public/
└── src/
    ├── main.jsx                         # React DOM entry point
    ├── App.jsx                          # Main router, tab-based navigation
    ├── index.css                        # Global CSS design system (custom properties,
    │                                    # dark theme, glassmorphism, micro-animations)
    ├── context/
    │   └── AuthContext.jsx              # Firebase Auth context provider
    ├── lib/
    │   └── api.js                       # Axios/fetch wrapper targeting Spring Boot
    │                                    # backend (http://localhost:8080)
    └── components/
        ├── Navbar.jsx                   # Top navigation bar
        ├── DashboardView.jsx            # Courses, assessments with status chips
        ├── CourseDetailView.jsx         # Document upload, CLO editor, assistant chat
        ├── NewAssessmentView.jsx        # Natural-language request + structured form
        ├── AssessmentDetailView.jsx     # Stepper: Blueprint → Pool → Review →
        │                                # Versions → Moderation → Export
        ├── AnalyticsView.jsx            # BigQuery-backed charts and cards
        └── AgentTraceDrawer.jsx         # Slide-out timeline of agent steps
```

---

## 4. DATA MODEL

Use in-memory `ConcurrentHashMap` collections in `DataStoreService.java` for the prototype (keyed by IDs). Migrate to Firestore for production. Every entity has `createdAt`, `updatedAt`, `createdBy` fields.

```
users/{uid}                     { email, displayName, role: "admin"|"lecturer"|"moderator"|"qa", institution,
                                  moderatorUid?: uid  (lecturers only: assigned by an admin),
                                  disabled: boolean }   # admin-managed; source of truth for role
courses/{courseId}              { code, title, ownerUid, clos: [CLO], topics: [Topic], confirmed: boolean }
  CLO   = { id: "CLO1", text, bloomLevel?: String }
  Topic = { id, name, cloIds: [] }
documents/{docId}               { courseId, kind: "syllabus"|"past_paper"|"rubric"|"qa_manual"|"notes",
                                  year?, gcsUri, textGcsUri, status, searchDocId }
pastItems/{id}                  { courseId, docId, year, text, embedding: double[] }   # extracted past questions
assessments/{assessmentId}      { courseId, title, request, totalMarks, durationMins, numVersions,
                                  status: "draft"|"blueprint_ready"|"pool_ready"|"reviewed"|
                                          "assembled"|"in_moderation"|"changes_requested"|"approved",
                                  runId, createdByUid, moderatorUid?, submittedAt? }
blueprints/{assessmentId}       { cells: [ {cloId, topicId, bloom, qType, count, marksEach} ],
                                  totals: {...}, valid: boolean, violations: [] }
items/{itemId}                  { assessmentId, stem, options?: [ {id, text} ], key, rationale,
                                  qType: "mcq"|"short_answer", marks, cloId, topicId,
                                  bloom: "remember"|"understand"|"apply"|"analyse"|"evaluate"|"create",
                                  bloomConfirmed: boolean, difficulty: 1-5, difficultySource:"ai"|"lecturer",
                                  sourceCitations: [ {docId, snippet, uri} ],
                                  status: "candidate"|"accepted"|"rejected", embedding }
flags/{flagId}                  { itemId, type: "key_mismatch"|"ambiguous"|"item_flaw"|"duplicate_past"|
                                  "duplicate_pool"|"misaligned_clo"|"bloom_doubt", severity, detail,
                                  evidence, resolution: null|"accepted"|"dismissed"|"edited", resolvedBy }
versions/{versionId}            { assessmentId, label: "A"|"B"|"C", itemIds: [], solverStats }
equivalenceReports/{assessmentId} { perVersion: {...}, deviations: {...}, guaranteed: [...],
                                  estimated: [...], limitations: [...], solverStatus }
moderation/{assessmentId}       { checklist: [...], aiComments: [...], humanComments: [...],
                                  decision: null|"approved"|"changes_requested", decidedBy }
runs/{runId}                    { assessmentId, steps: [ {agent, tool?, inputSummary, outputSummary,
                                  sources?, startedAt, endedAt, status} ] }   # powers the agent trace UI
audit/{id}                      { actorUid, action, entity, entityId, before?, after?, at }
notifications/{id}              { recipientUid, type: "submitted_for_moderation"|"moderation_approved"|
                                  "moderation_changes_requested"|"moderator_assigned",
                                  title, message, assessmentId?, actorName?, read: boolean, createdAt }
```

**Moderation workflow (status transitions):**

```
assembled ──(lecturer: submit)──▶ in_moderation ──(assigned moderator: approve)──▶ approved
                                       │
                                       └──(assigned moderator: request changes)──▶ changes_requested
changes_requested ──(lecturer: resubmit)──▶ in_moderation   # clears the previous decision, keeps comments
```

- Only the paper's owner (`createdByUid`) can submit, and only from `assembled` or `changes_requested`.
- Submitting copies the lecturer's current `moderatorUid` onto the assessment. Submission fails with a clear message if no active moderator is assigned.
- Only that moderator (or a QA officer) can decide, and only while the paper is `in_moderation`.
- Generating a moderation pack never changes the status on its own; only submission does.
- Visibility: lecturers see their own papers, moderators see papers submitted to them, admins and QA see all. Other users get `404`, not `403`.

**Java model notes:**
- All models are POJOs with Jackson `@JsonProperty` annotations and no-arg constructors.
- Request/response DTOs use separate classes (e.g. `CourseCreate`, `AssessmentCreate`, `ItemUpdate`, `FlagResolutionRequest`, `ModerationDecisionRequest`).
- Validation uses Jakarta Bean Validation annotations (`@NotNull`, `@NotBlank`, `@Min`, `@Max`).

---

## 5. AGENTS (ADK)

Implement each agent as an ADK `LlmAgent` (or the current equivalent) with a clear `instruction`, `output_schema` or structured output where supported, and tools. The **Orchestrator** coordinates sub-agents. A sequential workflow is fine: use ADK workflow agents such as `SequentialAgent` where helpful, but pause at human checkpoints. Implement checkpoints as separate API calls that resume the run, not as blocking waits.

**Integration with Spring Boot:** The ADK agents run as a Python sidecar service (e.g. a FastAPI microservice on an internal port, or a Cloud Run service). The Spring Boot backend invokes them via REST calls. Alternatively, for the prototype, agent logic can be simulated with mock responses in `DataStoreService`.

Every agent step must append a record to `runs/{runId}.steps` with a short input and output summary and any sources used. This feeds the **Agent Trace** UI, which is critical for judging.

### 5.1 DocIntel Agent
- **Input:** courseId.
- **Steps:** load documents, parse text, and extract structured JSON: CLOs, topics (mapped to CLOs), and past questions with year.
- **Parsing:** use `pdfplumber` or `python-docx` for digital files. If a PDF page has fewer than 50 extractable characters, send it to the **Document AI OCR processor**.
- **Indexing:** upload extracted text to the **Vertex AI Search** data store with metadata (`courseId`, `kind`, `year`). Compute embeddings for past questions.

### 5.2 Blueprint Agent
- **Input:** the request, confirmed CLOs and topics, and past paper structure.
- **Output:** blueprint cells (JSON) plus a short rationale.
- `validate_blueprint` (pure Java) checks that total marks equal the target, every CLO has more than 0 marks, and question-type counts are feasible. If violations exist, the agent repairs the blueprint up to 2 times.
- The lecturer edits it in the UI and re-validates.

### 5.3 Item Writer Agent
- For each blueprint cell, generate about 2.5× `count` candidates.
- **Must** call `search_knowledge_base(query, courseId, kinds=["syllabus","notes"])` first and ground each item in the retrieved passages. Each item must include `sourceCitations`; reject items without them.
- **MCQ rules:** 4 options, exactly 1 correct, plausible distractors, no "all/none of the above", no negative stems unless bolded, options of similar length.
- Include `rationale` (why the key is correct and why each distractor is wrong) and `difficulty` (1–5).
- Batch generation per cell for efficiency. Use `temperature` around 0.7 for variety.

### 5.4 Reviewer Agent (most important for trust)
Use a separate Gemini call with a different instruction from the writer. For each candidate:
1. **Independent solve:** give the stem and options **without the key**, ask for an answer with reasoning, and run it 3 times at temperature 0.7. If the majority answer differs from the key, raise a `key_mismatch` flag (high severity). If the 3 answers disagree with each other, raise an `ambiguous` flag.
2. **Flaw check:** look for ambiguous wording, missing information, cueing, implausible distractors, and multiple defensible answers.
3. **Alignment check:** confirm the item tests its CLO and Bloom's level. If not, raise `misaligned_clo` or `bloom_doubt` with a suggested level.
4. **Duplicates:** compare cosine similarity on embeddings against `pastItems` (threshold about 0.88, configurable), raising `duplicate_past` with the year. Also compare within the pool, raising `duplicate_pool`. Use Vertex AI Search as a secondary lexical check against past papers.

Use `temperature=0` for flaw and alignment checks. Parallelise across items with bounded concurrency.

### 5.5 Moderation Agent
- **Input:** versions, equivalence report, flags and resolutions, audit trail.
- **Output:** a moderator checklist, 3–6 drafted comments citing specific items, and an executive summary of the paper set.

### 5.6 Knowledge Assistant
- A chat agent with the `search_knowledge_base` tool across all of the course's documents.
- Answers must include citations (document title, year, snippet). If nothing relevant is found, say so and do not guess.

### 5.7 Prompt engineering requirements
- Store instructions in `agents/prompts/*.md` with a version header, and record the prompt version on every generated item.
- Use Gemini structured output (`response_schema`) with validated models.
- Include 1–2 short examples per prompt.
- Never include student personal data in prompts.

---

## 6. VERSION ASSEMBLY SOLVER (OR-TOOLS CP-SAT)

Implement `service/SolverService.java::assembleVersions(List<Item> items, Blueprint blueprint, int numVersions, List<ConflictPair> conflicts, int timeLimitSeconds)`.

- **Items:** only `status == "accepted"`, with no unresolved high-severity flags.
- **Variables:** `x[i][v] ∈ {0,1}`, where 1 means item *i* is in version *v*.

**Constraints:**
- Each item is in at most one version: `Σ_v x[i][v] ≤ 1`.
- For each version *v* and each blueprint cell *c* (CLO, topic, Bloom's level, question type, marks), `Σ_{i∈c} x[i][v] == count_c`. If the pool is too small for exact cell matching, fall back to matching marginal totals per CLO, per Bloom's level and per question type, and report which constraints were relaxed.
- Total marks per version equals the target.
- **Conflicts:** for every pair of items flagged `duplicate_pool` (or with similarity at or above the threshold), `x[i][v] + x[j][v] ≤ 1`, and ideally they are not used across versions either.

**Objective:**
- Use difficulty scaled ×10 as an integer.
- Minimise `max_v D_v - min_v D_v`, where `D_v = Σ_i difficulty_i·marks_i·x[i][v]` (marks-weighted difficulty).
- As a secondary objective, maximise lecturer-confirmed items.

**Output:** item IDs per version, solver status (OPTIMAL/FEASIBLE/INFEASIBLE), wall time and objective. If the problem is INFEASIBLE, return a human-readable diagnosis such as "CLO3 × apply × MCQ needs 4 items per version × 2 versions = 8, pool has 5 accepted".

`service/EquivalenceService.java` computes, per version:
- marks by CLO, Bloom's level, topic and question type;
- mean and SD of difficulty;
- the share of lecturer-confirmed tags.

It also computes deviations between versions and labels each metric **Guaranteed** (enforced by constraints) or **Estimated** (difficulty), with this fixed limitation text: *"Matching blueprints do not prove equal difficulty; empirical comparability requires student response data."*

**Unit tests (JUnit 5):** feasible case, infeasible case with diagnosis, conflict constraint respected, and totals exact.

---

## 7. FRONTEND (REACT + VITE + VANILLA CSS)

Aim for a clean, professional, accessible UI (WCAG AA contrast, keyboard navigable). Use a custom CSS design system with CSS custom properties, dark theme, glassmorphism effects, and micro-animations. Pages:

1. **Login** (Firebase Auth, email/password; no self sign-up, and no app header on this page). Seed users: `admin@demo`, `lecturer@demo` (assigned to `moderator@demo`), `moderator@demo`.
2. **Dashboard:** courses, assessments with status chips, and productivity summary cards. Lecturers see a **Your moderator** card (name, email, institution). Moderators see **Lecturers you moderate** and a count of papers awaiting review. Admins are redirected to the admin page.
3. **Admin: Users & assignments** (`/admin`, admin role only):
   - summary cards for lecturers, moderators, admins/QA, and lecturers without a moderator (highlighted as a warning);
   - **Create user** form: name, email, role, initial password, and an optional moderator for lecturers;
   - users table with an inline role selector, a moderator selector for each lecturer, and an Active/Disabled toggle;
   - an admin cannot demote or disable their own account. Demoting a moderator clears the assignments that pointed at them.
4. **Notifications:** a bell in the app header with an unread badge and a dropdown list. Clicking a notification opens its paper and marks it read; there is also "Mark all read". Poll every 30 seconds while the tab is visible.
5. **Course page:**
   - upload documents (drag-and-drop, choose the document type);
   - parsing status;
   - CLO and topic confirmation editor;
   - **Knowledge Assistant** chat side panel with citations.
6. **New Assessment:** a natural-language request box plus a structured form (marks, duration, versions, question types). Clicking "Start" launches the run.
7. **Assessment workspace** (stepper: Blueprint → Pool → Review → Versions → Moderation → Export):
   - **Blueprint:** editable matrix with live validation (red cells, total bar).
   - **Pool:** item cards with tags, citation chips (click to view the source snippet), and accept/edit/reject.
   - **Review:** flags grouped by severity. Each flag shows its evidence, such as "Independent solve chose B (3/3); key says C", or a side-by-side view of a past-paper duplicate with year. Actions: accept fix, dismiss, edit item.
   - **Versions:** side-by-side columns A, B (and C), plus the **Equivalence Report** with charts (Recharts bars by CLO and Bloom's level) and Guaranteed vs Estimated badges.
   - **Moderation:** AI checklist and comments, and a discussion thread.
     - Lecturer: their assigned moderator's contact details, then a **Submit for moderation** button (**Resubmit** after changes were requested). It is enabled only once the paper is assembled and a moderator is assigned. After submission it shows "Submitted on …, waiting for the moderator's decision".
     - Assigned moderator: Approve / Request changes, shown only while the paper is `in_moderation`.
   - **Export:** download PDF per version, the answer keys, Moodle XML and the CLO matrix CSV.
8. **Agent Trace** drawer, available on every assessment: a timeline of agent steps with agent name, tool calls, sources and duration. Update it live by polling `/api/runs/{id}` every 2 seconds.
9. **Analytics:** BigQuery-backed cards and charts (using Recharts) showing:
   - time per stage;
   - flags raised by type;
   - acceptance rate of AI suggestions;
   - estimated vs baseline time saved (baseline entered by the user, clearly labelled).

Every AI-generated element gets a subtle "AI suggestion" label. Human-confirmed elements get a check mark.

**Frontend design system:**
- CSS custom properties for colours, spacing, border-radius, shadows.
- Dark theme by default with glassmorphism panels.
- Smooth transitions and hover effects for interactive elements.
- Lucide React for iconography.
- No external CSS frameworks (no Tailwind, no Bootstrap).

---

## 8. API (SPRING BOOT) — MINIMUM ENDPOINTS

All endpoints are prefixed with `/api/`. Controllers use `@RestController` and `@RequestMapping`.

```
POST /api/courses                              GET /api/courses, /api/courses/{id}
POST /api/courses/{id}/documents               (multipart → GCS → parse job)
POST /api/courses/{id}/extract                 → DocIntel run
PUT  /api/courses/{id}/outcomes                (confirm CLOs/topics)
POST /api/courses/{id}/assistant               { question } → answer + citations
POST /api/assessments                          { courseId, request, totalMarks, durationMins, numVersions, qTypes }
POST /api/assessments/{id}/blueprint           → Blueprint agent
PUT  /api/assessments/{id}/blueprint           (edit+validate)
POST /api/assessments/{id}/pool                → ItemWriter
GET  /api/assessments/{id}/items               PATCH /api/items/{id}
POST /api/assessments/{id}/review              → Reviewer
GET  /api/assessments/{id}/flags               PATCH /api/flags/{id}
POST /api/assessments/{id}/assemble            → solver + equivalence
GET  /api/assessments/{id}/versions
POST /api/assessments/{id}/submit              (lecturer/owner → in_moderation, notifies the moderator)
POST /api/assessments/{id}/moderation          → Moderation agent
POST /api/assessments/{id}/decision            (assigned moderator; notifies the lecturer)
GET  /api/assessments/{id}/moderation
GET  /api/assessments/{id}/export?format=pdf|keys|moodle_xml|clo_csv&version=A
GET  /api/runs/{runId}
GET  /api/analytics/summary
GET  /api/me                                   → current user info
GET  /api/me/contacts                          → lecturer: assigned moderator; moderator: their lecturers
GET  /api/notifications                        POST /api/notifications/{id}/read, /api/notifications/read-all
GET  /api/admin/users                          POST /api/admin/users  (creates the Firebase account + role claim)
PATCH /api/admin/users/{uid}                   { displayName?, role?, institution?, disabled? }
PUT  /api/admin/users/{uid}/moderator          { moderatorUid | null }
GET  /api/system/health                        → health check
```

- Long-running steps return `202 Accepted` with a `runId` and run as `@Async` Spring tasks or `CompletableFuture`. The UI polls.
- Every mutating endpoint writes to `audit` and emits a BigQuery event.
- Role checks are enforced on the server via Spring Security filters or custom interceptors. `/api/admin/*` requires the `admin` role.
- Admin account changes go through the Firebase Admin SDK, which needs a service account. Disabling a user also revokes their refresh tokens.
- CORS is configured in `WebConfig.java` to allow the frontend origin.

---

## 9. SEED DATA AND DEMO COURSE

Create seed data within `DataStoreService.java` (loaded at startup via `@PostConstruct`) with a realistic **"CS2040 Database Systems"** course:
- a syllabus with 5 CLOs and 8 topics (ER modelling, normalisation, SQL basics, joins, transactions, indexing and so on);
- 2 lecture-note documents;
- a QA manual excerpt covering repeat-paper and moderation rules;
- **3 past papers (2023, 2024, 2025)** with about 15 questions each. All content is original and written by you.

Deliberately include past-paper questions that the generator is likely to reproduce, so the duplicate detector fires in the demo.

For standalone seed loading (production with Firestore), write `seed/load_seed.py` (or a Java equivalent `SeedDataLoader.java`) to create the users, the course and the documents, and run indexing.

Also create `seed/eval_set.json`: 60 MCQs, 12 of them with deliberately wrong keys and 6 near-duplicate pairs. Add `scripts/eval_reviewer.py` (or Java equivalent), which reports precision and recall of the Reviewer's `key_mismatch` and duplicate detection. These numbers go in the pitch.

---

## 10. GOOGLE CLOUD SETUP AND DEPLOYMENT

Write `infra/setup.sh` to be idempotent. Verify commands against current docs.

```bash
gcloud config set project $GCP_PROJECT_ID
gcloud services enable run.googleapis.com aiplatform.googleapis.com discoveryengine.googleapis.com \
  documentai.googleapis.com firestore.googleapis.com storage.googleapis.com bigquery.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com \
  identitytoolkit.googleapis.com

# Artifact Registry
gcloud artifacts repositories create $APP_NAME --repository-format=docker --location=$GCP_REGION

# Firestore (Native mode)
gcloud firestore databases create --location=$GCP_REGION

# Cloud Storage
gcloud storage buckets create gs://$GCP_PROJECT_ID-$APP_NAME --location=$GCP_REGION --uniform-bucket-level-access

# BigQuery
bq mk --location=$GCP_REGION --dataset $GCP_PROJECT_ID:assesscraft
bq mk --table assesscraft.events infra/bigquery_schema.json
#   schema: event_id STRING, ts TIMESTAMP, user_role STRING, assessment_id STRING, stage STRING,
#           event_type STRING, flag_type STRING, resolution STRING, duration_ms INT64, meta JSON

# Service account for backend
gcloud iam service-accounts create assesscraft-backend
#   grant: roles/aiplatform.user, roles/datastore.user, roles/storage.objectAdmin,
#          roles/discoveryengine.editor, roles/documentai.apiUser, roles/bigquery.dataEditor,
#          roles/bigquery.jobUser, roles/secretmanager.secretAccessor
```

**Manual or scripted steps (document in the README):**
- **Vertex AI Search:** create an unstructured data store (`assesscraft-docs`, location `global`) and a search app. Ingest documents from GCS with metadata. Store the IDs in env vars.
- **Document AI:** create an OCR processor in a supported region (`us` or `eu`). Store the processor ID.
- **Firebase:** add Firebase to the project, enable Email/Password and Google sign-in, and copy the web config into frontend env vars.

**Deploy:**
```bash
# backend (Spring Boot JAR in Docker)
gcloud builds submit assesscraft_backend --tag $GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/$APP_NAME/backend
gcloud run deploy assesscraft-api --image .../backend --region $GCP_REGION \
  --service-account assesscraft-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GCP_PROJECT_ID=...,GCP_REGION=...,GEMINI_MODEL=...,SEARCH_DATASTORE_ID=...,\
DOCAI_PROCESSOR_ID=...,BUCKET=...,BQ_DATASET=assesscraft,AGENT_RUNTIME=local \
  --memory 2Gi --cpu 2 --timeout 900 --min-instances 1 --allow-unauthenticated   # app enforces Firebase auth

# frontend (Vite static build served by nginx or node)
gcloud builds submit assesscraft_frontend --tag .../frontend
gcloud run deploy assesscraft-web --image .../frontend --region $GCP_REGION \
  --set-env-vars VITE_API_URL=<backend-url>,VITE_FIREBASE_API_KEY=...,VITE_FIREBASE_AUTH_DOMAIN=... \
  --allow-unauthenticated
```

Set `--min-instances 1` on the backend during judging so there are no cold starts. Restrict CORS to the frontend URL.

**Agent Engine (Milestone 7):** package the ADK orchestrator and deploy it with the Vertex AI SDK's Agent Engine API (`vertexai.agent_engines` or the current equivalent; check the docs). Expose its resource name via `AGENT_ENGINE_ID`, and route calls when `agent.runtime=agent_engine`.

**Security and data handling:**
- Use Vertex AI with no public web grounding.
- Never send student personal data to Gemini.
- Store secrets in Secret Manager.
- Give the service account least-privilege IAM.
- Make GCS objects private and serve downloads through signed URLs.
- Watermark PDFs with version label, assessment ID and "CONFIDENTIAL – DRAFT" until approved.

---

## 11. MILESTONES (STOP AFTER EACH, SUMMARISE, AND LIST WHAT TO VERIFY)

1. **Skeleton:** repos, Dockerfiles, Spring Boot health endpoint (`/api/system/health`), React app with auth, in-memory DataStore wiring, `infra/setup.sh`, first Cloud Run deploy of both services. *A deployed "hello" app with login is done.*
2. **Documents and knowledge:** upload, parse with Document AI fallback, Vertex AI Search indexing, seed loader, Knowledge Assistant with citations.
3. **Blueprint and Item Writer:** ADK agents (Python sidecar), structured outputs, validation, grounded citations, Pool UI, run tracing and the Agent Trace drawer.
4. **Reviewer:** independent solve with consistency checks, flaw checks, embeddings and duplicates, Review UI, plus `eval_reviewer.py` with reported metrics.
5. **Solver and equivalence:** CP-SAT assembly (Java OR-Tools) with JUnit tests, infeasibility diagnosis, Versions UI with Recharts charts.
6. **Moderation and export:** admin dashboard (accounts, roles, lecturer → moderator assignment), submit-for-moderation workflow, in-app notifications, Moderation agent, approval / request changes / resubmit, PDF/keys/Moodle XML/CSV exports, audit log.
7. **Analytics and Agent Engine:** BigQuery events and Recharts dashboard, Agent Engine deployment behind a flag, polish, README, `DEMO_SCRIPT.md`.

---

## 12. ACCEPTANCE CRITERIA (DEMO MUST PASS)

- [ ] On the deployed URL, the lecturer logs in, opens CS2040, and the assistant answers "Was a question on outer joins used before?" with a correct past-paper citation.
- [ ] The request "main + repeat paper, 100 marks" produces a valid blueprint in under 30 seconds.
- [ ] A pool is generated where every item has at least 1 citation and valid tags, in under 3 minutes.
- [ ] The Reviewer flags at least one key mismatch and at least one past-paper duplicate on seed data, with visible evidence.
- [ ] The solver returns 2 versions with exactly equal marks by CLO, Bloom's level and question type, and a difficulty gap shown; an infeasible configuration shows a clear diagnosis.
- [ ] The admin logs in, creates a lecturer and a moderator, and assigns the moderator to the lecturer; both see each other's contact details. A non-admin gets `403` on `/api/admin/*`.
- [ ] The lecturer submits an assembled paper; the assigned moderator gets a notification and, before submission, could not see the paper.
- [ ] The moderator requests changes; the lecturer is notified, resubmits, and the moderator approves.
- [ ] The moderator logs in, sees the AI checklist and comments, and approves; exports download correctly (PDF opens, Moodle XML imports into a test Moodle quiz bank or validates against the schema).
- [ ] The Agent Trace shows every agent step and tool call for the run.
- [ ] The Analytics page shows real logged events.
- [ ] JUnit tests pass; `eval_reviewer.py` prints precision and recall.
- [ ] The README lets a new developer deploy from scratch.

## 13. ENGINEERING RULES

- Type everything: Jackson-annotated POJOs with Jakarta Validation on the backend, JSX with PropTypes or JSDoc on the frontend. Use small, readable modules.
- Handle LLM failures gracefully with retries, timeouts and user-visible errors. Never leave the UI spinning forever.
- Log with structured JSON to Cloud Logging. Include `runId` in every log line.
- Do not hard-code secrets or project IDs. Use `application.properties` and environment variables.
- Keep costs low: use Flash by default, batch generation, cache embeddings, and use bounded concurrency.
- When unsure about a current Google Cloud API, look it up rather than guessing, and record the choice in `docs/DECISIONS.md`.
- At the end of each milestone, output: what was built, how to run or verify it, known issues, and the next step.

**Begin with Milestone 1.**
