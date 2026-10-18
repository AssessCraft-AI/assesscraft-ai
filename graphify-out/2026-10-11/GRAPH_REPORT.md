# Graph Report - AssessCraft_AI_Shaluka  (2026-10-11)

## Corpus Check
- 97 files · ~66,261 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 4, .ico 1, .css 1)

## Summary
- 685 nodes · 1759 edges · 36 communities (27 shown, 9 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 215 edges (avg confidence: 0.92)
- Token cost: 190,068 input · 1,200 output

## Community Hubs (Navigation)
- Item Writer & Moderation Agents
- Database Course Content
- Blueprint & Doc Intel Agents
- Assessments REST API
- Reviewer Quality Audit
- Agent Prompts & Build Spec
- PDF/DOCX Exporters
- Course Assistant & Documents
- Solver & Equivalence Engine
- Assessment Workspace UI
- Architecture Decisions & Stack
- Frontend Shell & New Assessment
- TypeScript Config
- Frontend Lint & Package Meta
- Orchestrator Pipeline
- Backend Deploy Script
- Firestore Service
- Course Page UI
- Frontend Dependencies
- Frontend Dev Dependencies
- Auth Context & API Client
- Analytics Dashboard UI
- Dashboard Home Page
- GCP Setup Script
- Frontend npm Scripts
- Firebase Auth Client
- Frontend Deploy Script
- Default UI Icons
- Gemini Model Selection
- Next.js & Vercel Logos
- Local Start Script
- Local Stop Script
- Build Milestones
- Backend Package

## God Nodes (most connected - your core abstractions)
1. `User` - 48 edges
2. `log_event()` - 38 edges
3. `Item` - 33 edges
4. `generate_id()` - 29 edges
5. `Assessment` - 24 edges
6. `run_item_writer_agent()` - 23 edges
7. `log_audit()` - 23 edges
8. `run_blueprint_agent()` - 22 edges
9. `run_moderation_agent()` - 22 edges
10. `run_reviewer_agent()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `CP-SAT Version Assembly Spec` --references--> `assemble_paper_versions()`  [EXTRACTED]
  AssessCraft_Build_Prompt.md → backend/app/tools/solver.py
- `Academic Equivalence Bounds (structural vs empirical)` --semantically_similar_to--> `Equivalence Report (Guaranteed vs Estimated)`  [INFERRED] [semantically similar]
  backend/app/agents/prompts/solver.md → AssessCraft_Build_Prompt.md
- `Difficulty Balance Objective` --conceptually_related_to--> `CP-SAT Version Assembly Spec`  [AMBIGUOUS]
  backend/app/agents/prompts/solver.md → AssessCraft_Build_Prompt.md
- `7-Act Evaluation Walkthrough` --implements--> `Demo Acceptance Criteria`  [INFERRED]
  docs/DEMO_SCRIPT.md → AssessCraft_Build_Prompt.md
- `Frontend README (create-next-app)` --conceptually_related_to--> `README`  [INFERRED]
  frontend/README.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Agent Prompt Pipeline (DocIntel -> Blueprint -> ItemWriter -> Reviewer -> Solver -> Moderation)** — backend_app_agents_prompts_doc_intel, backend_app_agents_prompts_blueprint, backend_app_agents_prompts_item_writer, backend_app_agents_prompts_reviewer, backend_app_agents_prompts_solver, backend_app_agents_prompts_moderation [EXTRACTED 1.00]
- **Deterministic Guarantees over LLM Output** — assesscraft_build_prompt_determinism_rule, docs_decisions_decision_003_or_tools, docs_decisions_adr_005_blueprint_rules_engine, docs_decisions_adr_008_cp_sat_assembly, backend_app_agents_prompts_solver_zero_item_overlap [INFERRED 0.85]
- **Grounding and Trust Mechanisms** — backend_app_agents_prompts_assistant_strict_grounding_rules, backend_app_agents_prompts_item_writer_source_citations, backend_app_agents_prompts_reviewer_independent_zero_shot_solve, docs_decisions_decision_008_grounded_citation, docs_decisions_adr_007_adversarial_reviewer [INFERRED 0.75]
- **CS2040 Past Paper Corpus (2023-2025) mapped to CLOs** — backend_seed_past_paper_2023_final_exam, backend_seed_past_paper_2024_final_exam, backend_seed_past_paper_2025_final_exam, backend_seed_syllabus_cs2040_cs2040_syllabus [INFERRED 0.85]
- **Main/Repeat Exam Equivalence Standards** — backend_seed_qa_manual_excerpt_structural_parity, backend_seed_qa_manual_excerpt_cognitive_balance, backend_seed_qa_manual_excerpt_zero_reuse_rule, backend_seed_qa_manual_excerpt_difficulty_variance [EXTRACTED 1.00]
- **Concurrency Anomalies vs Isolation Levels** — backend_seed_lecture_notes_transactions_dirty_read, backend_seed_lecture_notes_transactions_non_repeatable_read, backend_seed_lecture_notes_transactions_phantom_read, backend_seed_lecture_notes_transactions_ansi_isolation_levels [EXTRACTED 1.00]
- **create-next-app Default Public Assets** — frontend_public_file_fileicon, frontend_public_globe_globeicon, frontend_public_next_nextlogo, frontend_public_vercel_vercellogo, frontend_public_window_windowicon [INFERRED 0.85]

## Communities (36 total, 9 thin omitted)

### Community 0 - "Item Writer & Moderation Agents"
Cohesion: 0.08
Nodes (29): CellItemsResponse, GeneratedItemSchema, GeneratedOption, run_item_writer_agent(), ModerationAgentOutput, run_moderation_agent(), generate_item_pool(), patch_item() (+21 more)

### Community 1 - "Database Course Content"
Cohesion: 0.06
Nodes (62): B+ Tree, B+ Tree Height h = ceil(log_F N), Binary Search on Sorted File, Clustered (Primary) Index, Dr. Samantha Chen (Instructor), Heap File Scan, Doubly Linked Leaf Pages, CS2040 Lecture Notes: B+ Tree Indexing (+54 more)

### Community 2 - "Blueprint & Doc Intel Agents"
Cohesion: 0.07
Nodes (35): BlueprintResponse, run_blueprint_agent(), DocIntelResult, ExtractedPastQuestion, health_check(), lifespan(), log_requests(), root() (+27 more)

### Community 3 - "Assessments REST API"
Cohesion: 0.06
Nodes (30): get_analytics_summary(), create_assessment(), get_assessment(), list_assessments(), generate_blueprint(), get_blueprint(), update_blueprint(), create_course() (+22 more)

### Community 4 - "Reviewer Quality Audit"
Cohesion: 0.10
Nodes (24): run_doc_intel_extraction(), AlignmentOutput, audit_item_solve_3_runs(), check_item_alignment(), check_item_quality_flaws(), run_reviewer_agent(), review_single_item(), _solve_item_heuristic() (+16 more)

### Community 5 - "Agent Prompts & Build Spec"
Cohesion: 0.06
Nodes (28): Demo Acceptance Criteria, CP-SAT Version Assembly Spec, CS2040 Database Systems Seed Course, Equivalence Report (Guaranteed vs Estimated), Knowledge Assistant Agent Prompt v1.0, Blueprint Agent Prompt v1.0, Assessment Blueprint (CLO x Bloom x Topic x Type matrix), BlueprintResponse schema (+20 more)

### Community 6 - "PDF/DOCX Exporters"
Cohesion: 0.09
Nodes (9): export_assessment(), NumberedCanvas, render_clo_matrix_csv(), render_exam_pdf(), render_marking_guide_pdf(), render_moodle_xml(), test_exports_all_formats(), test_moderation_agent_generation() (+1 more)

### Community 7 - "Course Assistant & Documents"
Cohesion: 0.09
Nodes (15): answer_course_query(), ask_assistant(), AssistantAnswer, AssistantQuestion, trigger_extraction(), upload_document(), extract_document_text(), parse_docx() (+7 more)

### Community 8 - "Solver & Equivalence Engine"
Cohesion: 0.25
Nodes (11): run_solver_agent(), Blueprint, EquivalenceReport, PaperVersion, compute_equivalence_report(), assemble_paper_versions(), diagnose_infeasibility(), create_test_blueprint_and_items() (+3 more)

### Community 9 - "Assessment Workspace UI"
Cohesion: 0.12
Nodes (18): Assessment, AssessmentWorkspaceContent(), AssessmentWorkspacePage(), Blueprint, BlueprintCell, EquivalenceReport, Flag, Item (+10 more)

### Community 10 - "Architecture Decisions & Stack"
Cohesion: 0.12
Nodes (15): AssessCraft Build Prompt, Agent Trace (runs/{runId} steps), AssessCraft AI (Agentic Assessment Copilot), Firestore Data Model, Google Cloud AI Builder Cup 2026, Backend requirements.txt, google-adk, Architecture Decisions Log (+7 more)

### Community 11 - "Frontend Shell & New Assessment"
Cohesion: 0.18
Nodes (13): nextConfig, CourseOption, SAMPLE_PROMPTS, geistMono, geistSans, metadata, RootLayout(), LoginPage() (+5 more)

### Community 12 - "TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 13 - "Frontend Lint & Package Meta"
Cohesion: 0.12
Nodes (16): eslintConfig, name, private, version, clsx, eslint, eslint-config-next, react-dom (+8 more)

### Community 14 - "Orchestrator Pipeline"
Cohesion: 0.15
Nodes (6): AgentEngineClient, execute_workflow_stage(), run_full_assessment_pipeline(), test_agent_engine_runtime_flag(), test_analytics_summary_with_real_events(), test_orchestrator_stage_execution()

### Community 15 - "Backend Deploy Script"
Cohesion: 0.17
Nodes (11): AGENT_RUNTIME, APP_NAME, BQ_DATASET, BUCKET, DOCAI_PROCESSOR_ID, GCP_PROJECT_ID, GCP_REGION, GEMINI_MODEL (+3 more)

### Community 17 - "Course Page UI"
Cohesion: 0.20
Nodes (10): ChatMessage, Citation, CLO, Course, CoursePage(), CoursePageContent(), fetchCourseData(), DocumentItem (+2 more)

### Community 18 - "Frontend Dependencies"
Cohesion: 0.22
Nodes (9): dependencies, clsx, firebase, lucide-react, next, react, react-dom, recharts (+1 more)

### Community 19 - "Frontend Dev Dependencies"
Cohesion: 0.22
Nodes (9): devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/turbopack, @types/node, @types/react, @types/react-dom (+1 more)

### Community 20 - "Auth Context & API Client"
Cohesion: 0.33
Nodes (7): AuthContext, AuthContextType, DEMO_PERSONAS, API_BASE_URL, apiDownload(), getStoredUser(), UserSession

### Community 21 - "Analytics Dashboard UI"
Cohesion: 0.25
Nodes (6): AnalyticsData, AnalyticsPage(), FlagCount, StageTiming, TelemetryEvent, lucide-react

### Community 22 - "Dashboard Home Page"
Cohesion: 0.32
Nodes (6): NewAssessmentPage(), CourseData, DashboardPage(), loadData(), HealthData, apiRequest()

### Community 23 - "GCP Setup Script"
Cohesion: 0.29
Nodes (6): APP_NAME, DOCAI_REGION, GCP_PROJECT_ID, GCP_REGION, setup.sh script, VERTEX_SEARCH_LOC

### Community 24 - "Frontend npm Scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, start

### Community 25 - "Firebase Auth Client"
Cohesion: 0.40
Nodes (4): auth, firebaseConfig, googleProvider, firebase

### Community 26 - "Frontend Deploy Script"
Cohesion: 0.40
Nodes (4): APP_NAME, GCP_PROJECT_ID, GCP_REGION, deploy_frontend.sh script

### Community 27 - "Default UI Icons"
Cohesion: 0.67
Nodes (3): File Document Icon, Globe Icon, Browser Window Icon

## Ambiguous Edges - Review These
- `CP-SAT Version Assembly Spec` → `Difficulty Balance Objective`  [AMBIGUOUS]
  backend/app/agents/prompts/solver.md · relation: conceptually_related_to
- `Blueprint Agent Prompt v1.0` → `7-Act Evaluation Walkthrough`  [AMBIGUOUS]
  backend/app/agents/prompts/blueprint.md · relation: conceptually_related_to
- `Cosine Similarity Duplicate Detection` → `ADR 007: Adversarial Reviewer & Vector Duplicate Detection`  [AMBIGUOUS]
  docs/DECISIONS.md · relation: conceptually_related_to
- `CS2040 Assessment Scheme (60% Final, 20 MCQ x2 + 10 SAQ x6)` → `CS2040 Final Examination 2023 (Section A MCQ)`  [AMBIGUOUS]
  backend/seed/past_paper_2023.md · relation: conceptually_related_to

## Knowledge Gaps
- **53 isolated node(s):** `assesscraft-backend`, `clsx`, `react-dom`, `tailwind-merge`, `@tailwindcss/turbopack` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 265 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ADR 007: Adversarial Reviewer & Vector Duplicate Detection` connect `Agent Prompts & Build Spec` to `Reviewer Quality Audit`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `User` (e.g. with `get_analytics_summary()` and `create_assessment()`) actually correct?**
  _`User` has 32 INFERRED edges - model-reasoned connections that need verification._
- **What connects `assesscraft-backend`, `clsx`, `react-dom` to the rest of the system?**
  _53 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Item Writer & Moderation Agents` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Why does `7-Act Evaluation Walkthrough` connect `Agent Prompts & Build Spec` to `Architecture Decisions & Stack`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `CP-SAT Version Assembly Spec` and `Difficulty Balance Objective`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Blueprint Agent Prompt v1.0` and `7-Act Evaluation Walkthrough`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._