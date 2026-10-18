# Graph Report - AssessCraft_AI_Shaluka  (2026-10-15)

## Corpus Check
- 129 files · ~98,662 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 8, .toml 1, .example 1)

## Summary
- 1155 nodes · 2888 edges · 74 communities (45 shown, 29 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 270 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `63dd8d84`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Item
- CS2040 Database Systems Syllabus
- CP-SAT Version Assembly Spec
- package.json
- cloud_start.sh
- test_adk_agents.py
- test_firebase_auth.py
- execute_workflow_stage
- models.py
- main.py
- item_writer.py
- doc_intel.py
- reviewer.py
- test_milestone2.py
- AuthContext.tsx
- [id]/page.tsx
- similarity.py
- compilerOptions
- export_assessment
- users/page.tsx
- apiRequest
- seed_database
- analytics/page.tsx
- [code]/page.tsx
- courses.py
- FirestoreService
- test_multi_role.py
- admin.py
- Components
- blueprint.py
- review_assessment
- generate_item_pool
- RunTrace
- User
- pytest
- Agent Hosting Decision (Cloud Run first, Agent Engine later)
- setup.sh
- me.py
- lib.sh
- log_event
- ask_assistant
- smoke_test.sh
- cloud_stop.sh
- seed_production.sh
- log_requests
- DECISION-005: Firebase Auth and RBAC
- Browser Window Icon
- Next.js Wordmark Logo
- start_local.sh script
- stop_local.sh
- Build Milestones 1-7
- Assessment
- Backend requirements.txt
- google-adk
- google-genai
- ortools
- pdfplumber
- reportlab
- assesscraft-backend
- Pitch Metrics (98.8% faster, 100% reviewer P/R)
- AdminData.tsx
- Product
- StageAgent
- 2026-10-13T11-34-18Z__frontend-src.md
- run_pipeline_with_adk
- test_agent_engine_runtime_flag
- 2026-10-13T12-07-21Z__frontend-src.md
- build_orchestrator
- generate_blueprint
- trigger_assembly

## God Nodes (most connected - your core abstractions)
1. `User` - 75 edges
2. `Item` - 40 edges
3. `log_event()` - 39 edges
4. `seed_database()` - 31 edges
5. `generate_id()` - 30 edges
6. `log_audit()` - 30 edges
7. `current_time_iso()` - 27 edges
8. `Assessment` - 25 edges
9. `apiRequest()` - 25 edges
10. `run_moderation_agent()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `CP-SAT Version Assembly Spec` --references--> `assemble_paper_versions()`  [EXTRACTED]
  AssessCraft_Build_Prompt.md → backend/app/tools/solver.py
- `Academic Equivalence Bounds (structural vs empirical)` --semantically_similar_to--> `Equivalence Report (Guaranteed vs Estimated)`  [INFERRED] [semantically similar]
  backend/app/agents/prompts/solver.md → AssessCraft_Build_Prompt.md
- `Difficulty Balance Objective` --conceptually_related_to--> `CP-SAT Version Assembly Spec`  [AMBIGUOUS]
  backend/app/agents/prompts/solver.md → AssessCraft_Build_Prompt.md
- `ADR 007: Adversarial Reviewer & Vector Duplicate Detection` --conceptually_related_to--> `Cosine Similarity Duplicate Detection`  [AMBIGUOUS]
  docs/DECISIONS.md → backend/app/agents/prompts/reviewer.md
- `Blueprint Agent Prompt v1.0` --conceptually_related_to--> `7-Act Evaluation Walkthrough`  [AMBIGUOUS]
  backend/app/agents/prompts/blueprint.md → docs/DEMO_SCRIPT.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Agent Prompt Pipeline (DocIntel -> Blueprint -> ItemWriter -> Reviewer -> Solver -> Moderation)** — backend_app_agents_prompts_doc_intel, backend_app_agents_prompts_blueprint, backend_app_agents_prompts_item_writer, backend_app_agents_prompts_reviewer, backend_app_agents_prompts_solver, backend_app_agents_prompts_moderation [EXTRACTED 1.00]
- **Concurrency Anomalies vs Isolation Levels** — backend_seed_lecture_notes_transactions_dirty_read, backend_seed_lecture_notes_transactions_non_repeatable_read, backend_seed_lecture_notes_transactions_phantom_read, backend_seed_lecture_notes_transactions_ansi_isolation_levels [EXTRACTED 1.00]
- **Main/Repeat Exam Equivalence Standards** — backend_seed_qa_manual_excerpt_structural_parity, backend_seed_qa_manual_excerpt_cognitive_balance, backend_seed_qa_manual_excerpt_zero_reuse_rule, backend_seed_qa_manual_excerpt_difficulty_variance [EXTRACTED 1.00]
- **Grounding and Trust Mechanisms** — backend_app_agents_prompts_assistant_strict_grounding_rules, backend_app_agents_prompts_item_writer_source_citations, backend_app_agents_prompts_reviewer_independent_zero_shot_solve, docs_decisions_decision_008_grounded_citation, docs_decisions_adr_007_adversarial_reviewer [INFERRED 0.75]
- **Deterministic Guarantees over LLM Output** — assesscraft_build_prompt_determinism_rule, docs_decisions_decision_003_or_tools, docs_decisions_adr_005_blueprint_rules_engine, docs_decisions_adr_008_cp_sat_assembly, backend_app_agents_prompts_solver_zero_item_overlap [INFERRED 0.85]
- **create-next-app Default Public Assets** — frontend_public_file_fileicon, frontend_public_globe_globeicon, frontend_public_next_nextlogo, frontend_public_vercel_vercellogo, frontend_public_window_windowicon [INFERRED 0.85]
- **CS2040 Past Paper Corpus (2023-2025) mapped to CLOs** — backend_seed_past_paper_2023_final_exam, backend_seed_past_paper_2024_final_exam, backend_seed_past_paper_2025_final_exam, backend_seed_syllabus_cs2040_cs2040_syllabus [INFERRED 0.85]

## Communities (74 total, 29 thin omitted)

### Community 0 - "Item"
Cohesion: 0.16
Nodes (24): BlueprintResponse, run_solver_agent(), Blueprint, BlueprintCell, EquivalenceReport, Item, Option, PaperVersion (+16 more)

### Community 1 - "CS2040 Database Systems Syllabus"
Cohesion: 0.06
Nodes (62): B+ Tree, B+ Tree Height h = ceil(log_F N), Binary Search on Sorted File, Clustered (Primary) Index, Dr. Samantha Chen (Instructor), Heap File Scan, Doubly Linked Leaf Pages, CS2040 Lecture Notes: B+ Tree Indexing (+54 more)

### Community 2 - "CP-SAT Version Assembly Spec"
Cohesion: 0.05
Nodes (33): AssessCraft Build Prompt, Demo Acceptance Criteria, AssessCraft AI (Agentic Assessment Copilot), CP-SAT Version Assembly Spec, CS2040 Database Systems Seed Course, Equivalence Report (Guaranteed vs Estimated), Google Cloud AI Builder Cup 2026, Knowledge Assistant Agent Prompt v1.0 (+25 more)

### Community 3 - "package.json"
Cohesion: 0.05
Nodes (39): eslintConfig, dependencies, clsx, firebase, lucide-react, next, react, react-dom (+31 more)

### Community 4 - "cloud_start.sh"
Cohesion: 0.05
Nodes (36): AGENT_RUNTIME, ALLOWED_EMAIL_DOMAINS, APP_NAME, BQ_DATASET, BUCKET, DEFAULT_ROLE, DOCAI_PROCESSOR_ID, GCP_PROJECT_ID (+28 more)

### Community 5 - "test_adk_agents.py"
Cohesion: 0.23
Nodes (5): run_stage_with_adk(), setup_seed_data(), test_pipeline_runs_stages_in_order_via_sequential_agent(), test_single_stage_runs_through_adk_runner(), test_unknown_stage_is_rejected()

### Community 6 - "test_firebase_auth.py"
Cohesion: 0.12
Nodes (17): health_check(), lifespan(), root(), gemini_configured(), firebase_only(), _get(), test_check_gemini_reports_unconfigured(), test_domain_allow_list() (+9 more)

### Community 7 - "execute_workflow_stage"
Cohesion: 0.27
Nodes (3): AgentEngineClient, execute_workflow_stage(), run_full_assessment_pipeline()

### Community 8 - "models.py"
Cohesion: 0.12
Nodes (24): can_view(), get_assessment(), get_visible_assessment(), is_owner(), is_paper_moderator(), list_assessments(), role_on_paper(), add_moderation_comment() (+16 more)

### Community 10 - "item_writer.py"
Cohesion: 0.11
Nodes (13): run_stage_impl(), answer_course_query(), CellItemsResponse, GeneratedItemSchema, GeneratedOption, run_item_writer_agent(), ModerationAgentOutput, run_moderation_agent() (+5 more)

### Community 11 - "doc_intel.py"
Cohesion: 0.27
Nodes (6): DocIntelResult, ExtractedPastQuestion, run_doc_intel_extraction(), process_single_cell(), compute_embeddings(), require_gemini_or_fallback()

### Community 12 - "reviewer.py"
Cohesion: 0.15
Nodes (15): AlignmentOutput, audit_item_solve_3_runs(), check_item_alignment(), check_item_quality_flaws(), _lexical_past_duplicate(), review_single_item(), _solve_item_heuristic(), solve_item_single_run() (+7 more)

### Community 13 - "test_milestone2.py"
Cohesion: 0.05
Nodes (21): upload_document(), _deliver(), _get_bucket(), is_configured(), _sign_sync(), upload_and_sign(), upload_bytes(), _upload_sync() (+13 more)

### Community 14 - "AuthContext.tsx"
Cohesion: 0.18
Nodes (17): AuthContext, AuthContextType, DEMO_PERSONAS, MeResponse, PLACEHOLDER, API_BASE_URL, apiDownload(), getAuthHeaders() (+9 more)

### Community 15 - "[id]/page.tsx"
Cohesion: 0.09
Nodes (31): Assessment, AssessmentWorkspaceContent(), AssessmentWorkspacePage(), Blueprint, BlueprintCell, ContactSummary, EquivalenceReport, Flag (+23 more)

### Community 16 - "similarity.py"
Cohesion: 0.09
Nodes (11): Settings, check_gemini(), cosine_similarity(), find_similar_items(), _stable_bucket(), evaluate_duplicates(), main(), report() (+3 more)

### Community 17 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 18 - "export_assessment"
Cohesion: 0.28
Nodes (4): export_assessment(), render_exam_pdf(), render_marking_guide_pdf(), render_moodle_xml()

### Community 19 - "users/page.tsx"
Cohesion: 0.12
Nodes (49): AssignmentsPage(), PersonSelect(), Scope, View, DeleteModuleModal(), formatDate(), ModuleFilter, ModuleFormModal() (+41 more)

### Community 20 - "apiRequest"
Cohesion: 0.09
Nodes (28): nextConfig, CourseOption, NewAssessmentPage(), SAMPLE_PROMPTS, geistMono, geistSans, metadata, RootLayout() (+20 more)

### Community 21 - "seed_database"
Cohesion: 0.08
Nodes (13): resolve_flag(), Document, PastItem, seed_database(), _deck(), setup(), test_upload_slides_and_model_paper(), setup_seed_data() (+5 more)

### Community 22 - "analytics/page.tsx"
Cohesion: 0.29
Nodes (5): AnalyticsData, AnalyticsPage(), FlagCount, StageTiming, TelemetryEvent

### Community 23 - "[code]/page.tsx"
Cohesion: 0.13
Nodes (19): ChatMessage, Citation, CLO, Course, CoursePage(), CoursePageContent(), fetchCourseData(), Topic (+11 more)

### Community 24 - "courses.py"
Cohesion: 0.11
Nodes (19): create_assessment(), submit_for_moderation(), course_contacts(), create_course(), delete_course(), get_course(), _grant_moderator_role(), list_courses() (+11 more)

### Community 26 - "test_multi_role.py"
Cohesion: 0.08
Nodes (27): _call(), create_account(), EmailAlreadyExists, IdentityUnavailable, _role_claims(), update_account(), client(), _notes() (+19 more)

### Community 27 - "admin.py"
Cohesion: 0.13
Nodes (17): AdminUserView, _clear_module_moderator(), create_user(), _get_user_or_404(), _is_firebase_uid(), list_users(), _sync_account(), update_user() (+9 more)

### Community 28 - "Components"
Cohesion: 0.07
Nodes (28): Agent Trace Drawer (signature), Buttons, Cards / Containers, Chips, Colors, Components, Design System: AssessCraft AI, Do: (+20 more)

### Community 29 - "blueprint.py"
Cohesion: 0.22
Nodes (11): run_blueprint_agent(), seed_default_data(), CLO, Topic, repair_blueprint(), validate_blueprint(), setup_test_data(), test_api_milestone3_workflow() (+3 more)

### Community 32 - "RunTrace"
Cohesion: 0.31
Nodes (4): get_run_trace(), RunStep, RunTrace, RunTracker

### Community 33 - "User"
Cohesion: 0.10
Nodes (13): get_blueprint(), list_documents(), trigger_extraction(), list_flags(), list_items(), list_notifications(), mark_all_read(), mark_read() (+5 more)

### Community 34 - "pytest"
Cohesion: 0.21
Nodes (6): _enable_demo_auth_for_tests(), test_analytics_summary(), test_courses_list_and_seed(), test_demo_headers_rejected_when_demo_auth_disabled(), test_health_endpoint(), test_root_endpoint()

### Community 35 - "Agent Hosting Decision (Cloud Run first, Agent Engine later)"
Cohesion: 0.29
Nodes (3): Agent Trace (runs/{runId} steps), Firestore Data Model, Dual Multi-Agent Runtime (AGENT_RUNTIME=local|agent_engine)

### Community 36 - "setup.sh"
Cohesion: 0.29
Nodes (6): APP_NAME, DOCAI_REGION, GCP_PROJECT_ID, GCP_REGION, setup.sh script, VERTEX_SEARCH_LOC

### Community 37 - "me.py"
Cohesion: 0.17
Nodes (11): _active(), me(), module_contacts(), module_moderator_uid(), ModuleContacts, my_contacts(), MyContacts, _summary() (+3 more)

### Community 39 - "log_event"
Cohesion: 0.12
Nodes (7): get_analytics_summary(), update_blueprint(), patch_item(), get_all_events(), get_bq_client(), log_event(), test_analytics_summary_with_real_events()

### Community 40 - "ask_assistant"
Cohesion: 0.50
Nodes (3): ask_assistant(), AssistantAnswer, AssistantQuestion

### Community 41 - "smoke_test.sh"
Cohesion: 0.60
Nodes (3): fail(), pass(), smoke_test.sh script

### Community 42 - "cloud_stop.sh"
Cohesion: 0.50
Nodes (3): GCP_PROJECT_ID, GCP_REGION, cloud_stop.sh script

### Community 43 - "seed_production.sh"
Cohesion: 0.50
Nodes (3): GCP_PROJECT_ID, GCP_REGION, seed_production.sh script

### Community 46 - "Browser Window Icon"
Cohesion: 0.67
Nodes (3): File Document Icon, Globe Icon, Browser Window Icon

### Community 52 - "Assessment"
Cohesion: 0.31
Nodes (8): run_reviewer_agent(), Assessment, compute_embedding(), setup_test_data(), test_reviewer_3_run_ambiguity_and_alignment_detection(), test_reviewer_api_workflow_and_flag_resolution(), test_reviewer_key_mismatch_and_flaw_detection(), test_reviewer_past_exam_and_pool_duplicate_detection()

### Community 63 - "AdminData.tsx"
Cohesion: 0.29
Nodes (9): AdminLayout(), AdminDataContext, AdminDataProvider(), AdminDataValue, AdminUser, fetchAll(), ToastProvider(), UserTitle (+1 more)

### Community 64 - "Product"
Cohesion: 0.20
Nodes (9): Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product, Product Principles, Product Purpose (+1 more)

### Community 66 - "2026-10-13T11-34-18Z__frontend-src.md"
Cohesion: 0.29
Nodes (6): Design Health Score: 18/40 (Poor), Design Specificity, Minor, Persona Red Flags, Priority Issues, Questions

### Community 69 - "2026-10-13T12-07-21Z__frontend-src.md"
Cohesion: 0.40
Nodes (4): Design Health Score: 19/40 (Poor) — run 1: 18/40, Detector, Persona Red Flags, Priority Issues

## Ambiguous Edges - Review These
- `CP-SAT Version Assembly Spec` → `Difficulty Balance Objective`  [AMBIGUOUS]
  backend/app/agents/prompts/solver.md · relation: conceptually_related_to
- `Cosine Similarity Duplicate Detection` → `ADR 007: Adversarial Reviewer & Vector Duplicate Detection`  [AMBIGUOUS]
  docs/DECISIONS.md · relation: conceptually_related_to
- `7-Act Evaluation Walkthrough` → `Blueprint Agent Prompt v1.0`  [AMBIGUOUS]
  backend/app/agents/prompts/blueprint.md · relation: conceptually_related_to
- `CS2040 Assessment Scheme (60% Final, 20 MCQ x2 + 10 SAQ x6)` → `CS2040 Final Examination 2023 (Section A MCQ)`  [AMBIGUOUS]
  backend/seed/past_paper_2023.md · relation: conceptually_related_to

## Knowledge Gaps
- **84 isolated node(s):** `assesscraft-backend`, `clsx`, `react-dom`, `tailwind-merge`, `@tailwindcss/turbopack` (+79 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 474 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `User` to `RunTrace`, `me.py`, `log_event`, `models.py`, `main.py`, `ask_assistant`, `generate_blueprint`, `trigger_assembly`, `test_milestone2.py`, `export_assessment`, `seed_database`, `courses.py`, `admin.py`, `review_assessment`, `generate_item_pool`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `User` (e.g. with `create_user()` and `list_users()`) actually correct?**
  _`User` has 52 INFERRED edges - model-reasoned connections that need verification._
- **What connects `assesscraft-backend`, `clsx`, `react-dom` to the rest of the system?**
  _84 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CS2040 Database Systems Syllabus` be split into smaller, more focused modules?**
  _Cohesion score 0.06317907444668008 - nodes in this community are weakly interconnected._
- **Why does `assemble_paper_versions()` connect `Item` to `CP-SAT Version Assembly Spec`, `item_writer.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `CP-SAT Version Assembly Spec` and `Difficulty Balance Objective`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cosine Similarity Duplicate Detection` and `ADR 007: Adversarial Reviewer & Vector Duplicate Detection`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._