# Graph Report - AssessCraft_AI_Shaluka  (2026-10-13)

## Corpus Check
- 105 files · ~74,317 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 7, .toml 1, .example 1)

## Summary
- 861 nodes · 2115 edges · 46 communities (27 shown, 19 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 228 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e4466346`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_milestone2.py
- Item
- CS2040 Database Systems Syllabus
- exporters.py
- CP-SAT Version Assembly Spec
- test_firebase_auth.py
- package.json
- adk_agents.py
- models.py
- reviewer.py
- storage.py
- AuthContext.tsx
- [id]/page.tsx
- compilerOptions
- [code]/page.tsx
- useAuth
- cloud_start.sh
- FirestoreService
- layout.tsx
- execute_workflow_stage
- lib.sh
- item_writer.py
- Agent Hosting Decision (Cloud Run first, Agent Engine later)
- analytics/page.tsx
- setup.sh
- smoke_test.sh
- seed_production.sh
- DECISION-005: Firebase Auth and RBAC
- Browser Window Icon
- Next.js Wordmark Logo
- start_local.sh
- stop_local.sh
- Build Milestones 1-7
- Backend requirements.txt
- google-adk
- google-genai
- ortools
- pdfplumber
- reportlab
- assesscraft-backend
- Pitch Metrics (98.8% faster, 100% reviewer P/R)
- log_requests
- cloud_stop.sh

## God Nodes (most connected - your core abstractions)
1. `User` - 53 edges
2. `Item` - 40 edges
3. `log_event()` - 38 edges
4. `generate_id()` - 30 edges
5. `seed_database()` - 25 edges
6. `run_moderation_agent()` - 24 edges
7. `Assessment` - 24 edges
8. `log_audit()` - 23 edges
9. `run_blueprint_agent()` - 22 edges
10. `run_item_writer_agent()` - 22 edges

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

## Communities (46 total, 19 thin omitted)

### Community 0 - "test_milestone2.py"
Cohesion: 0.19
Nodes (12): answer_course_query(), ask_assistant(), AssistantAnswer, AssistantQuestion, SourceCitation, get_discovery_client(), search_knowledge_base(), test_assistant_api_endpoint() (+4 more)

### Community 1 - "Item"
Cohesion: 0.13
Nodes (25): BlueprintResponse, run_solver_agent(), Blueprint, BlueprintCell, EquivalenceReport, Item, Option, PaperVersion (+17 more)

### Community 2 - "CS2040 Database Systems Syllabus"
Cohesion: 0.06
Nodes (62): B+ Tree, B+ Tree Height h = ceil(log_F N), Binary Search on Sorted File, Clustered (Primary) Index, Dr. Samantha Chen (Instructor), Heap File Scan, Doubly Linked Leaf Pages, CS2040 Lecture Notes: B+ Tree Indexing (+54 more)

### Community 3 - "exporters.py"
Cohesion: 0.08
Nodes (10): export_assessment(), NumberedCanvas, render_clo_matrix_csv(), render_exam_pdf(), render_marking_guide_pdf(), render_moodle_xml(), extract_document_text(), parse_docx() (+2 more)

### Community 4 - "CP-SAT Version Assembly Spec"
Cohesion: 0.05
Nodes (33): AssessCraft Build Prompt, Demo Acceptance Criteria, AssessCraft AI (Agentic Assessment Copilot), CP-SAT Version Assembly Spec, CS2040 Database Systems Seed Course, Equivalence Report (Guaranteed vs Estimated), Google Cloud AI Builder Cup 2026, Knowledge Assistant Agent Prompt v1.0 (+25 more)

### Community 5 - "test_firebase_auth.py"
Cohesion: 0.08
Nodes (24): deep_health_check(), health_check(), lifespan(), root(), check_gemini(), gemini_configured(), firebase_only(), _get() (+16 more)

### Community 6 - "package.json"
Cohesion: 0.05
Nodes (39): eslintConfig, dependencies, clsx, firebase, lucide-react, next, react, react-dom (+31 more)

### Community 7 - "adk_agents.py"
Cohesion: 0.09
Nodes (11): build_orchestrator(), _build_stage_agent(), run_pipeline_with_adk(), run_stage_with_adk(), _run_with_runner(), StageAgent, setup_seed_data(), test_orchestrator_is_an_adk_sequential_agent_over_all_stages() (+3 more)

### Community 8 - "models.py"
Cohesion: 0.05
Nodes (54): ModerationAgentOutput, run_moderation_agent(), get_analytics_summary(), create_assessment(), get_assessment(), list_assessments(), get_blueprint(), update_blueprint() (+46 more)

### Community 9 - "reviewer.py"
Cohesion: 0.09
Nodes (21): AlignmentOutput, audit_item_solve_3_runs(), check_item_alignment(), check_item_quality_flaws(), _lexical_past_duplicate(), review_single_item(), _solve_item_heuristic(), solve_item_single_run() (+13 more)

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

### Community 16 - "cloud_start.sh"
Cohesion: 0.05
Nodes (34): AGENT_RUNTIME, ALLOWED_EMAIL_DOMAINS, APP_NAME, BQ_DATASET, BUCKET, DEFAULT_ROLE, DOCAI_PROCESSOR_ID, GCP_PROJECT_ID (+26 more)

### Community 18 - "layout.tsx"
Cohesion: 0.32
Nodes (6): geistMono, geistSans, metadata, RootLayout(), Navbar(), AuthProvider()

### Community 19 - "execute_workflow_stage"
Cohesion: 0.08
Nodes (11): AgentEngineClient, execute_workflow_stage(), run_full_assessment_pipeline(), generate_blueprint(), review_assessment(), generate_item_pool(), trigger_assembly(), setup_seed_data() (+3 more)

### Community 22 - "item_writer.py"
Cohesion: 0.06
Nodes (41): run_stage_impl(), run_blueprint_agent(), DocIntelResult, ExtractedPastQuestion, run_doc_intel_extraction(), CellItemsResponse, GeneratedItemSchema, GeneratedOption (+33 more)

### Community 23 - "Agent Hosting Decision (Cloud Run first, Agent Engine later)"
Cohesion: 0.29
Nodes (3): Agent Trace (runs/{runId} steps), Firestore Data Model, Dual Multi-Agent Runtime (AGENT_RUNTIME=local|agent_engine)

### Community 24 - "analytics/page.tsx"
Cohesion: 0.29
Nodes (5): AnalyticsData, AnalyticsPage(), FlagCount, StageTiming, TelemetryEvent

### Community 25 - "setup.sh"
Cohesion: 0.29
Nodes (6): APP_NAME, DOCAI_REGION, GCP_PROJECT_ID, GCP_REGION, setup.sh script, VERTEX_SEARCH_LOC

### Community 27 - "smoke_test.sh"
Cohesion: 0.60
Nodes (3): fail(), pass(), smoke_test.sh script

### Community 28 - "seed_production.sh"
Cohesion: 0.50
Nodes (3): GCP_PROJECT_ID, GCP_REGION, seed_production.sh script

### Community 31 - "Browser Window Icon"
Cohesion: 0.67
Nodes (3): File Document Icon, Globe Icon, Browser Window Icon

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 361 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `assemble_paper_versions()` connect `Item` to `CP-SAT Version Assembly Spec`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `User` (e.g. with `get_analytics_summary()` and `create_assessment()`) actually correct?**
  _`User` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `assesscraft-backend`, `clsx`, `react-dom` to the rest of the system?**
  _82 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Item` be split into smaller, more focused modules?**
  _Cohesion score 0.13002114164904863 - nodes in this community are weakly interconnected._
- **Why does `CP-SAT Version Assembly Spec` connect `CP-SAT Version Assembly Spec` to `Item`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `CP-SAT Version Assembly Spec` and `Difficulty Balance Objective`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cosine Similarity Duplicate Detection` and `ADR 007: Adversarial Reviewer & Vector Duplicate Detection`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._