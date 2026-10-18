# Graph Report - AssessCraft_AI_Shaluka  (2026-10-16)

## Corpus Check
- 137 files · ~104,669 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 8, .toml 1, .example 1)

## Summary
- 1253 nodes · 3173 edges · 76 communities (55 shown, 21 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 281 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `63368320`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- seed_database
- CS2040 Database Systems Syllabus
- courses.py
- test_milestone2.py
- users/page.tsx
- CP-SAT Version Assembly Spec
- api/moderation.py
- models.py
- Item
- package.json
- exporters.py
- cloud_start.sh
- adk_agents.py
- [id]/page.tsx
- react
- admin.py
- Components
- reviewer.py
- apiRequest
- AuthContext.tsx
- purge_assessments_without_clos.py
- asyncio
- compilerOptions
- test_multi_role.py
- test_audit_must_fixes.py
- config.py
- storage.py
- test_access_control.py
- Product
- traces.py
- item_writer.py
- ask_assistant
- User
- test_health.py
- Agent Hosting Decision (Cloud Run first, Agent Engine later)
- analytics/page.tsx
- 2026-10-13T11-34-18Z__frontend-src.md
- setup.sh
- lib.sh
- Assessment
- 2026-10-13T12-07-21Z__frontend-src.md
- smoke_test.sh
- cloud_stop.sh
- seed_production.sh
- test_firebase_auth.py
- DECISION-005: Firebase Auth and RBAC
- Browser Window Icon
- Next.js Wordmark Logo
- start_local.sh script
- stop_local.sh
- Build Milestones 1-7
- me.py
- AdminData.tsx
- new/page.tsx
- log_event
- test_document_kinds.py
- Backend requirements.txt
- google-adk
- google-genai
- ortools
- pdfplumber
- reportlab
- assesscraft-backend
- Pitch Metrics (98.8% faster, 100% reviewer P/R)
- 2026-10-15T16-33-52Z__frontend-src.md
- assessments.py
- NumberedCanvas
- AgentEngineClient
- parsing.py
- log_requests
- 2026-10-15T16-40-29Z__frontend-src.md
- 2026-10-16T05-33-08Z__frontend-src.md

## God Nodes (most connected - your core abstractions)
1. `User` - 78 edges
2. `Item` - 40 edges
3. `log_event()` - 38 edges
4. `seed_database()` - 35 edges
5. `log_audit()` - 33 edges
6. `generate_id()` - 30 edges
7. `current_time_iso()` - 27 edges
8. `Assessment` - 26 edges
9. `run_blueprint_agent()` - 25 edges
10. `get_visible_assessment()` - 25 edges

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

## Communities (76 total, 21 thin omitted)

### Community 0 - "seed_database"
Cohesion: 0.13
Nodes (24): BlueprintResponse, run_blueprint_agent(), update_blueprint(), seed_default_data(), AssessmentCreate, BlueprintCell, CLO, Course (+16 more)

### Community 1 - "CS2040 Database Systems Syllabus"
Cohesion: 0.06
Nodes (62): B+ Tree, B+ Tree Height h = ceil(log_F N), Binary Search on Sorted File, Clustered (Primary) Index, Dr. Samantha Chen (Instructor), Heap File Scan, Doubly Linked Leaf Pages, CS2040 Lecture Notes: B+ Tree Indexing (+54 more)

### Community 2 - "courses.py"
Cohesion: 0.09
Nodes (18): course_contacts(), create_course(), delete_course(), get_course(), _grant_moderator_role(), list_courses(), _notify_assignments(), require_course_owner() (+10 more)

### Community 3 - "test_milestone2.py"
Cohesion: 0.27
Nodes (10): answer_course_query(), SourceCitation, get_discovery_client(), search_knowledge_base(), test_assistant_api_endpoint(), test_knowledge_assistant_outer_joins_query(), test_knowledge_assistant_qa_manual_repeat_paper(), test_local_search_cites_relevant_passage_from_full_text() (+2 more)

### Community 4 - "users/page.tsx"
Cohesion: 0.10
Nodes (56): AssignmentsPage(), PersonSelect(), Scope, View, DeleteModuleModal(), formatDate(), ModuleFilter, ModuleFormModal() (+48 more)

### Community 5 - "CP-SAT Version Assembly Spec"
Cohesion: 0.05
Nodes (33): AssessCraft Build Prompt, Demo Acceptance Criteria, AssessCraft AI (Agentic Assessment Copilot), CP-SAT Version Assembly Spec, CS2040 Database Systems Seed Course, Equivalence Report (Guaranteed vs Estimated), Google Cloud AI Builder Cup 2026, Knowledge Assistant Agent Prompt v1.0 (+25 more)

### Community 6 - "api/moderation.py"
Cohesion: 0.17
Nodes (17): ModerationAgentOutput, run_moderation_agent(), add_moderation_comment(), generate_moderation_pack(), HumanCommentRequest, _lecturer_uid(), submit_moderation_decision(), AuditEntry (+9 more)

### Community 7 - "models.py"
Cohesion: 0.22
Nodes (6): list_documents(), get_current_user(), require_role(), _user_from_firebase_claims(), Document, ItemUpdate

### Community 8 - "Item"
Cohesion: 0.17
Nodes (22): run_solver_agent(), Blueprint, EquivalenceReport, Item, Option, PaperVersion, compute_equivalence_report(), assemble_paper_versions() (+14 more)

### Community 9 - "package.json"
Cohesion: 0.05
Nodes (39): eslintConfig, dependencies, clsx, firebase, lucide-react, next, react, react-dom (+31 more)

### Community 10 - "exporters.py"
Cohesion: 0.13
Nodes (6): render_clo_matrix_csv(), render_exam_pdf(), render_marking_guide_pdf(), render_moodle_xml(), _sections(), test_sections_number_questions_continuously()

### Community 11 - "cloud_start.sh"
Cohesion: 0.05
Nodes (36): AGENT_RUNTIME, ALLOWED_EMAIL_DOMAINS, APP_NAME, BQ_DATASET, BUCKET, DEFAULT_ROLE, DOCAI_PROCESSOR_ID, GCP_PROJECT_ID (+28 more)

### Community 12 - "adk_agents.py"
Cohesion: 0.09
Nodes (11): build_orchestrator(), _build_stage_agent(), run_pipeline_with_adk(), run_stage_with_adk(), _run_with_runner(), StageAgent, setup_seed_data(), test_orchestrator_is_an_adk_sequential_agent_over_all_stages() (+3 more)

### Community 13 - "[id]/page.tsx"
Cohesion: 0.08
Nodes (34): Assessment, AssessmentWorkspaceContent(), AssessmentWorkspacePage(), Blueprint, BlueprintCell, ContactSummary, EquivalenceReport, Flag (+26 more)

### Community 14 - "react"
Cohesion: 0.15
Nodes (15): nextConfig, geistMono, geistSans, metadata, RootLayout(), LoginPage(), Navbar(), AppNotification (+7 more)

### Community 15 - "admin.py"
Cohesion: 0.09
Nodes (23): AdminUserView, _clear_module_moderator(), create_user(), _get_user_or_404(), _is_firebase_uid(), list_users(), _sync_account(), update_user() (+15 more)

### Community 16 - "Components"
Cohesion: 0.07
Nodes (28): Agent Trace Drawer (signature), Buttons, Cards / Containers, Chips, Colors, Components, Design System: AssessCraft AI, Do: (+20 more)

### Community 17 - "reviewer.py"
Cohesion: 0.11
Nodes (20): AlignmentOutput, audit_item_solve_3_runs(), check_item_alignment(), check_item_quality_flaws(), _lexical_past_duplicate(), review_single_item(), _solve_item_heuristic(), solve_item_single_run() (+12 more)

### Community 18 - "apiRequest"
Cohesion: 0.12
Nodes (22): ChatMessage, Citation, CLO, Course, CoursePage(), CoursePageContent(), fetchCourseData(), Topic (+14 more)

### Community 19 - "AuthContext.tsx"
Cohesion: 0.18
Nodes (18): AuthContext, AuthContextType, AuthProvider(), DEMO_PERSONAS, MeResponse, PLACEHOLDER, API_BASE_URL, apiDownload() (+10 more)

### Community 20 - "purge_assessments_without_clos.py"
Cohesion: 0.27
Nodes (6): delete_assessment(), delete_assessment_data(), find_targets(), main(), purge(), test_purge_removes_only_papers_of_modules_without_outcomes()

### Community 21 - "asyncio"
Cohesion: 0.25
Nodes (3): test_export_uses_signed_url_when_storage_is_configured(), test_exports_all_formats(), test_moderation_rbac_and_decision()

### Community 22 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 23 - "test_multi_role.py"
Cohesion: 0.11
Nodes (22): client(), _notes(), setup(), test_admin_cannot_lock_themselves_out(), test_admin_creates_users_and_assigns_moderator(), test_demo_records_are_not_provisioned_and_labels_are_not_names(), test_lecturer_sees_assigned_moderator_contact(), test_one_lecturer_two_modules_two_moderators() (+14 more)

### Community 24 - "test_audit_must_fixes.py"
Cohesion: 0.21
Nodes (8): _cell(), client(), _of(), setup(), test_blueprint_put_recomputes_validity_on_the_server(), test_redraft_replaces_the_pool(), test_rerun_review_keeps_examiner_decisions(), test_strict_mode_never_mixes_hash_embeddings()

### Community 25 - "config.py"
Cohesion: 0.14
Nodes (3): Settings, main(), _enable_demo_auth_for_tests()

### Community 26 - "storage.py"
Cohesion: 0.22
Nodes (7): _deliver(), _get_bucket(), is_configured(), _sign_sync(), upload_and_sign(), upload_bytes(), _upload_sync()

### Community 27 - "test_access_control.py"
Cohesion: 0.09
Nodes (17): FirestoreService, client(), _ids(), _paper_routes(), setup(), test_cloud_errors_are_not_swallowed(), test_export_of_missing_version_is_404_not_the_draft_pool(), test_internal_errors_do_not_leak_details() (+9 more)

### Community 28 - "Product"
Cohesion: 0.20
Nodes (9): Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product, Product Principles, Product Purpose (+1 more)

### Community 29 - "traces.py"
Cohesion: 0.43
Nodes (3): RunStep, RunTrace, RunTracker

### Community 30 - "item_writer.py"
Cohesion: 0.15
Nodes (11): DocIntelResult, ExtractedPastQuestion, run_doc_intel_extraction(), CellItemsResponse, GeneratedItemSchema, GeneratedOption, run_item_writer_agent(), process_single_cell() (+3 more)

### Community 31 - "ask_assistant"
Cohesion: 0.50
Nodes (3): ask_assistant(), AssistantAnswer, AssistantQuestion

### Community 32 - "User"
Cohesion: 0.10
Nodes (21): get_editable_assessment(), get_visible_assessment(), generate_blueprint(), get_blueprint(), export_assessment(), list_flags(), resolve_flag(), review_assessment() (+13 more)

### Community 33 - "test_health.py"
Cohesion: 0.39
Nodes (5): test_analytics_summary(), test_courses_list_and_seed(), test_demo_headers_rejected_when_demo_auth_disabled(), test_health_endpoint(), test_root_endpoint()

### Community 34 - "Agent Hosting Decision (Cloud Run first, Agent Engine later)"
Cohesion: 0.29
Nodes (3): Agent Trace (runs/{runId} steps), Firestore Data Model, Dual Multi-Agent Runtime (AGENT_RUNTIME=local|agent_engine)

### Community 35 - "analytics/page.tsx"
Cohesion: 0.29
Nodes (5): AnalyticsData, AnalyticsPage(), FlagCount, StageTiming, TelemetryEvent

### Community 36 - "2026-10-13T11-34-18Z__frontend-src.md"
Cohesion: 0.29
Nodes (6): Design Health Score: 18/40 (Poor), Design Specificity, Minor, Persona Red Flags, Priority Issues, Questions

### Community 37 - "setup.sh"
Cohesion: 0.29
Nodes (6): APP_NAME, DOCAI_REGION, GCP_PROJECT_ID, GCP_REGION, setup.sh script, VERTEX_SEARCH_LOC

### Community 39 - "Assessment"
Cohesion: 0.18
Nodes (10): run_stage_impl(), run_reviewer_agent(), Assessment, compute_embedding(), _stable_bucket(), setup_test_data(), test_reviewer_3_run_ambiguity_and_alignment_detection(), test_reviewer_api_workflow_and_flag_resolution() (+2 more)

### Community 40 - "2026-10-13T12-07-21Z__frontend-src.md"
Cohesion: 0.40
Nodes (4): Design Health Score: 19/40 (Poor) — run 1: 18/40, Detector, Persona Red Flags, Priority Issues

### Community 41 - "smoke_test.sh"
Cohesion: 0.60
Nodes (3): fail(), pass(), smoke_test.sh script

### Community 42 - "cloud_stop.sh"
Cohesion: 0.50
Nodes (3): GCP_PROJECT_ID, GCP_REGION, cloud_stop.sh script

### Community 43 - "seed_production.sh"
Cohesion: 0.50
Nodes (3): GCP_PROJECT_ID, GCP_REGION, seed_production.sh script

### Community 44 - "test_firebase_auth.py"
Cohesion: 0.09
Nodes (22): deep_health_check(), health_check(), lifespan(), root(), check_gemini(), find_similar_items(), gemini_configured(), firebase_only() (+14 more)

### Community 46 - "Browser Window Icon"
Cohesion: 0.67
Nodes (3): File Document Icon, Globe Icon, Browser Window Icon

### Community 52 - "me.py"
Cohesion: 0.20
Nodes (10): _active(), me(), module_contacts(), module_moderator_uid(), ModuleContacts, my_contacts(), MyContacts, _summary() (+2 more)

### Community 53 - "AdminData.tsx"
Cohesion: 0.29
Nodes (9): AdminLayout(), AdminDataContext, AdminDataProvider(), AdminDataValue, AdminUser, fetchAll(), ToastProvider(), UserTitle (+1 more)

### Community 54 - "new/page.tsx"
Cohesion: 0.20
Nodes (9): CourseOption, NewAssessmentPage(), OFF, QType, QTYPES, SAMPLE_PROMPTS, totalsOf(), TypeRow (+1 more)

### Community 55 - "log_event"
Cohesion: 0.12
Nodes (9): execute_workflow_stage(), get_analytics_summary(), get_all_events(), get_bq_client(), log_event(), setup_seed_data(), test_agent_engine_runtime_flag(), test_analytics_summary_with_real_events() (+1 more)

### Community 56 - "test_document_kinds.py"
Cohesion: 0.29
Nodes (3): _deck(), setup(), test_upload_slides_and_model_paper()

### Community 68 - "2026-10-15T16-33-52Z__frontend-src.md"
Cohesion: 0.25
Nodes (7): Design Health Score: 25/40 (Acceptable) — run 1: 18/40, run 2: 19/40, Design Specificity Verdict, Detector Findings, Minor Observations, Persona Red Flags, Priority Issues, Questions to Consider

### Community 69 - "assessments.py"
Cohesion: 0.15
Nodes (12): can_view(), create_assessment(), get_assessment(), is_owner(), is_paper_moderator(), list_assessments(), role_on_paper(), submit_for_moderation() (+4 more)

### Community 72 - "parsing.py"
Cohesion: 0.24
Nodes (5): extract_document_text(), parse_docx(), parse_pdf_plumber(), parse_pptx(), parse_with_document_ai_ocr()

### Community 76 - "2026-10-15T16-40-29Z__frontend-src.md"
Cohesion: 0.40
Nodes (4): Design Health Score: 30/40 (Good) — run 1: 18/40, run 2: 19/40, run 3: 25/40, Design Specificity Verdict, Detector Findings, Priority Issues

### Community 77 - "2026-10-16T05-33-08Z__frontend-src.md"
Cohesion: 0.40
Nodes (4): Design Health Score: 32/40 (Good) — run 1: 18/40, run 2: 19/40, run 3: 25/40, run 4: 30/40, Design Specificity Verdict, Detector Findings, Priority Issues

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 515 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `assemble_paper_versions()` connect `Item` to `CP-SAT Version Assembly Spec`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `User` (e.g. with `create_user()` and `list_users()`) actually correct?**
  _`User` has 55 INFERRED edges - model-reasoned connections that need verification._
- **What connects `assesscraft-backend`, `clsx`, `react-dom` to the rest of the system?**
  _84 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `seed_database` be split into smaller, more focused modules?**
  _Cohesion score 0.12579281183932348 - nodes in this community are weakly interconnected._
- **Why does `CP-SAT Version Assembly Spec` connect `CP-SAT Version Assembly Spec` to `Item`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `CP-SAT Version Assembly Spec` and `Difficulty Balance Objective`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cosine Similarity Duplicate Detection` and `ADR 007: Adversarial Reviewer & Vector Duplicate Detection`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._