# Graph Report - AssessCraft_AI_Shaluka  (2026-10-12)

## Corpus Check
- 104 files · ~73,893 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 5, .toml 1, .example 1)

## Summary
- 850 nodes · 2082 edges · 58 communities (38 shown, 20 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 224 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f16aceab`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- generate_id
- Item
- CS2040 Database Systems Syllabus
- test_milestone2.py
- CP-SAT Version Assembly Spec
- test_firebase_auth.py
- package.json
- adk_agents.py
- User
- reviewer.py
- storage.py
- AuthContext.tsx
- [id]/page.tsx
- compilerOptions
- [code]/page.tsx
- useAuth
- deploy_backend.sh
- FirestoreService
- set_user_role.py
- execute_workflow_stage
- items.py
- main.py
- layout.tsx
- Agent Hosting Decision (Cloud Run first, Agent Engine later)
- analytics/page.tsx
- setup.sh
- deploy_frontend.sh
- smoke_test.sh
- seed_production.sh
- log_requests
- DECISION-005: Firebase Auth and RBAC
- Browser Window Icon
- Next.js Wordmark Logo
- start_local.sh
- stop_local.sh
- Build Milestones 1-7
- log_event
- Backend requirements.txt
- google-adk
- google-genai
- ortools
- pdfplumber
- reportlab
- assesscraft-backend
- Pitch Metrics (98.8% faster, 100% reviewer P/R)
- similarity.py
- cloud_start.sh
- models.py
- eval_reviewer.py
- item_writer.py
- assessments.py
- doc_intel.py
- events.py
- upload_document
- cloud_stop.sh

## God Nodes (most connected - your core abstractions)
1. `User` - 53 edges
2. `Item` - 39 edges
3. `log_event()` - 38 edges
4. `generate_id()` - 30 edges
5. `seed_database()` - 25 edges
6. `Assessment` - 24 edges
7. `run_moderation_agent()` - 23 edges
8. `log_audit()` - 23 edges
9. `run_item_writer_agent()` - 22 edges
10. `Blueprint` - 22 edges

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

## Communities (58 total, 20 thin omitted)

### Community 0 - "generate_id"
Cohesion: 0.09
Nodes (21): ModerationAgentOutput, run_moderation_agent(), add_moderation_comment(), generate_moderation_pack(), get_moderation_record(), HumanCommentRequest, submit_moderation_decision(), Comment (+13 more)

### Community 1 - "Item"
Cohesion: 0.07
Nodes (51): run_stage_impl(), BlueprintResponse, run_blueprint_agent(), run_item_writer_agent(), run_reviewer_agent(), run_solver_agent(), seed_default_data(), Assessment (+43 more)

### Community 2 - "CS2040 Database Systems Syllabus"
Cohesion: 0.06
Nodes (62): B+ Tree, B+ Tree Height h = ceil(log_F N), Binary Search on Sorted File, Clustered (Primary) Index, Dr. Samantha Chen (Instructor), Heap File Scan, Doubly Linked Leaf Pages, CS2040 Lecture Notes: B+ Tree Indexing (+54 more)

### Community 3 - "test_milestone2.py"
Cohesion: 0.06
Nodes (19): answer_course_query(), ask_assistant(), AssistantAnswer, AssistantQuestion, export_assessment(), NumberedCanvas, render_clo_matrix_csv(), render_exam_pdf() (+11 more)

### Community 4 - "CP-SAT Version Assembly Spec"
Cohesion: 0.05
Nodes (33): AssessCraft Build Prompt, Demo Acceptance Criteria, AssessCraft AI (Agentic Assessment Copilot), CP-SAT Version Assembly Spec, CS2040 Database Systems Seed Course, Equivalence Report (Guaranteed vs Estimated), Google Cloud AI Builder Cup 2026, Knowledge Assistant Agent Prompt v1.0 (+25 more)

### Community 5 - "test_firebase_auth.py"
Cohesion: 0.10
Nodes (17): lifespan(), _enable_demo_auth_for_tests(), firebase_only(), _get(), test_domain_allow_list(), test_email_never_elevates_role(), test_invalid_token_is_401(), test_lecturer_cannot_use_moderator_endpoint() (+9 more)

### Community 6 - "package.json"
Cohesion: 0.05
Nodes (39): eslintConfig, dependencies, clsx, firebase, lucide-react, next, react, react-dom (+31 more)

### Community 7 - "adk_agents.py"
Cohesion: 0.09
Nodes (11): build_orchestrator(), _build_stage_agent(), run_pipeline_with_adk(), run_stage_with_adk(), _run_with_runner(), StageAgent, setup_seed_data(), test_orchestrator_is_an_adk_sequential_agent_over_all_stages() (+3 more)

### Community 8 - "User"
Cohesion: 0.17
Nodes (8): get_blueprint(), me(), get_run_trace(), get_equivalence_report(), get_version_items(), list_versions(), trigger_assembly(), User

### Community 9 - "reviewer.py"
Cohesion: 0.14
Nodes (11): AlignmentOutput, audit_item_solve_3_runs(), check_item_alignment(), check_item_quality_flaws(), _lexical_past_duplicate(), review_single_item(), _solve_item_heuristic(), solve_item_single_run() (+3 more)

### Community 10 - "storage.py"
Cohesion: 0.22
Nodes (7): _deliver(), _get_bucket(), is_configured(), _sign_sync(), upload_and_sign(), upload_bytes(), _upload_sync()

### Community 11 - "AuthContext.tsx"
Cohesion: 0.17
Nodes (18): AuthContext, AuthContextType, DEMO_PERSONAS, MeResponse, PLACEHOLDER, Role, API_BASE_URL, apiDownload() (+10 more)

### Community 12 - "[id]/page.tsx"
Cohesion: 0.12
Nodes (18): Assessment, AssessmentWorkspaceContent(), AssessmentWorkspacePage(), Blueprint, BlueprintCell, EquivalenceReport, Flag, Item (+10 more)

### Community 13 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 14 - "[code]/page.tsx"
Cohesion: 0.16
Nodes (14): NewAssessmentPage(), ChatMessage, Citation, CLO, Course, CoursePage(), CoursePageContent(), fetchCourseData() (+6 more)

### Community 15 - "useAuth"
Cohesion: 0.22
Nodes (10): nextConfig, CourseOption, SAMPLE_PROMPTS, LoginPage(), CourseData, HealthData, useAuth(), lucide-react (+2 more)

### Community 16 - "deploy_backend.sh"
Cohesion: 0.12
Nodes (15): AGENT_RUNTIME, ALLOWED_EMAIL_DOMAINS, APP_NAME, BQ_DATASET, BUCKET, DEFAULT_ROLE, DOCAI_PROCESSOR_ID, GCP_PROJECT_ID (+7 more)

### Community 19 - "execute_workflow_stage"
Cohesion: 0.12
Nodes (8): AgentEngineClient, execute_workflow_stage(), run_full_assessment_pipeline(), generate_blueprint(), review_assessment(), test_agent_engine_runtime_flag(), test_analytics_summary_with_real_events(), test_orchestrator_stage_execution()

### Community 20 - "items.py"
Cohesion: 0.25
Nodes (4): generate_item_pool(), list_items(), patch_item(), ItemUpdate

### Community 21 - "main.py"
Cohesion: 0.21
Nodes (3): get_current_user(), _user_from_firebase_claims(), Settings

### Community 22 - "layout.tsx"
Cohesion: 0.32
Nodes (6): geistMono, geistSans, metadata, RootLayout(), Navbar(), AuthProvider()

### Community 23 - "Agent Hosting Decision (Cloud Run first, Agent Engine later)"
Cohesion: 0.29
Nodes (3): Agent Trace (runs/{runId} steps), Firestore Data Model, Dual Multi-Agent Runtime (AGENT_RUNTIME=local|agent_engine)

### Community 24 - "analytics/page.tsx"
Cohesion: 0.29
Nodes (5): AnalyticsData, AnalyticsPage(), FlagCount, StageTiming, TelemetryEvent

### Community 25 - "setup.sh"
Cohesion: 0.29
Nodes (6): APP_NAME, DOCAI_REGION, GCP_PROJECT_ID, GCP_REGION, setup.sh script, VERTEX_SEARCH_LOC

### Community 26 - "deploy_frontend.sh"
Cohesion: 0.40
Nodes (4): APP_NAME, GCP_PROJECT_ID, GCP_REGION, deploy_frontend.sh script

### Community 27 - "smoke_test.sh"
Cohesion: 0.60
Nodes (3): fail(), pass(), smoke_test.sh script

### Community 28 - "seed_production.sh"
Cohesion: 0.50
Nodes (3): GCP_PROJECT_ID, GCP_REGION, seed_production.sh script

### Community 31 - "Browser Window Icon"
Cohesion: 0.67
Nodes (3): File Document Icon, Globe Icon, Browser Window Icon

### Community 37 - "log_event"
Cohesion: 0.16
Nodes (9): update_blueprint(), create_course(), get_course(), list_courses(), update_course_outcomes(), CourseCreate, CourseOutcomesUpdate, log_audit() (+1 more)

### Community 48 - "similarity.py"
Cohesion: 0.11
Nodes (10): deep_health_check(), health_check(), root(), check_gemini(), find_similar_items(), gemini_configured(), get_genai_client(), _stable_bucket() (+2 more)

### Community 49 - "cloud_start.sh"
Cohesion: 0.12
Nodes (15): AGENT_RUNTIME, ALLOWED_EMAIL_DOMAINS, APP_NAME, BQ_DATASET, BUCKET, DEFAULT_ROLE, DOCAI_PROCESSOR_ID, GCP_PROJECT_ID (+7 more)

### Community 50 - "models.py"
Cohesion: 0.26
Nodes (5): list_documents(), list_flags(), resolve_flag(), AuditEntry, FlagResolutionRequest

### Community 51 - "eval_reviewer.py"
Cohesion: 0.24
Nodes (8): cosine_similarity(), evaluate_duplicates(), evaluate_key_mismatch(), run(), main(), report(), scores(), to_reviewer_item()

### Community 52 - "item_writer.py"
Cohesion: 0.32
Nodes (6): CellItemsResponse, GeneratedItemSchema, GeneratedOption, SourceCitation, get_discovery_client(), search_knowledge_base()

### Community 53 - "assessments.py"
Cohesion: 0.22
Nodes (5): create_assessment(), get_assessment(), list_assessments(), require_role(), AssessmentCreate

### Community 54 - "doc_intel.py"
Cohesion: 0.29
Nodes (5): DocIntelResult, ExtractedPastQuestion, run_doc_intel_extraction(), require_gemini_or_fallback(), test_strict_mode_forbids_fallback_content()

### Community 55 - "events.py"
Cohesion: 0.28
Nodes (3): get_analytics_summary(), get_all_events(), get_bq_client()

### Community 57 - "cloud_stop.sh"
Cohesion: 0.50
Nodes (3): GCP_PROJECT_ID, GCP_REGION, cloud_stop.sh script

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
- **82 isolated node(s):** `assesscraft-backend`, `clsx`, `react-dom`, `tailwind-merge`, `@tailwindcss/turbopack` (+77 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 354 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `assemble_paper_versions()` connect `Item` to `CP-SAT Version Assembly Spec`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `User` (e.g. with `get_analytics_summary()` and `create_assessment()`) actually correct?**
  _`User` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `assesscraft-backend`, `clsx`, `react-dom` to the rest of the system?**
  _82 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `generate_id` be split into smaller, more focused modules?**
  _Cohesion score 0.09191583610188261 - nodes in this community are weakly interconnected._
- **Why does `CP-SAT Version Assembly Spec` connect `CP-SAT Version Assembly Spec` to `Item`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `CP-SAT Version Assembly Spec` and `Difficulty Balance Objective`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cosine Similarity Duplicate Detection` and `ADR 007: Adversarial Reviewer & Vector Duplicate Detection`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._