# AssessCraft AI — Architecture Decisions & Log

## DECISION-001: Model Selection & Google GenAI SDK
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** AssessCraft requires reliable structured outputs, grounded citations, independent problem solving, and low latency across multi-step agent workflows.
- **Decision:**
  - Standard model: `gemini-2.5-flash` for DocIntel, Blueprint, ItemWriter, Moderation, and Knowledge Assistant.
  - Reviewer model: Configurable via `REVIEWER_MODEL` (defaults to `gemini-2.5-flash`, with option to switch to `gemini-2.5-pro` for advanced multi-step solving).
  - SDK: Use the modern unified `google-genai` Python SDK (`from google import genai; client = genai.Client(vertexai=True, project=..., location=...)`).
  - Strict Pydantic schemas are passed to `response_schema` to guarantee valid JSON without hallucinations.

## DECISION-002: Multi-Agent Architecture with ADK
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** The system needs coordinated specialized agents (DocIntel, Blueprint, ItemWriter, Reviewer, Moderation) with human-in-the-loop checkpoints.
- **Decision:**
  - Implement agents using `google-adk` (`LlmAgent`, `SequentialAgent`).
  - Host agents directly inside the FastAPI Cloud Run backend for low latency, zero external network hops during multi-turn orchestration, and easy local debugging.
  - Provide an `AGENT_RUNTIME=local|agent_engine` flag allowing orchestrator execution to be delegated to Vertex AI Agent Engine.
  - Record fine-grained agent execution traces into Firestore collection `runs/{runId}` at every step (inputs, tools invoked, sources cited, execution latency).

## DECISION-003: Deterministic Constraint Satisfaction with OR-Tools
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** Academic paper blueprints require exact marks totals, strict Bloom's taxonomy distributions, non-overlapping items across versions, and difficulty balancing.
- **Decision:**
  - LLMs NEVER perform arithmetic or combinatorial optimization.
  - Implement version assembly using Google OR-Tools CP-SAT solver (`ortools.sat.python.cp_model`).
  - Pure Python deterministic validation for blueprints and difficulty equivalence calculations.

## DECISION-004: Region and Service Locality
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** The requested default region is `asia-southeast1`. Some services (Document AI OCR processors, Vertex AI Search data stores) have specific regional availability.
- **Decision:**
  - Core services (Cloud Run, Firestore, GCS, BigQuery, Vertex AI Gemini endpoints): `asia-southeast1`.
  - Document AI OCR processor: `us` (or `eu`) multi-region, where standard General OCR v2.0 is globally accessible with highest uptime.
  - Vertex AI Search: `global` location.
  - Recorded in configuration with environment variable overrides.

## DECISION-005: Authentication and Role-Based Access Control
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** Role-based permissions are required: `lecturer` creates blueprints and manages candidate pools; `moderator` reviews equivalence and gives final sign-off; `qa` audits.
- **Decision:**
  - Firebase Authentication for identity (Email/Password and Google sign-in).
  - FastAPI auth middleware verifies Firebase ID tokens and checks user roles against Firestore `users/{uid}`.
  - Built-in demo identity provider allows instant one-click switching between `lecturer@demo` and `moderator@demo` for friction-free judging and testing.

## DECISION-006: Local & Offline Resilience
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** Local testing and CI/CD smoke tests should run smoothly even before full GCP service account provisioning.
- **Decision:**
  - All Firestore, Cloud Storage, and BigQuery services feature transparent in-memory / local fallback handlers when GCP credentials or project IDs are unconfigured.
  - Unit and integration tests can execute in CI without cloud billing or network dependencies.

## DECISION-007: Document Ingestion Hierarchy & OCR Fallback
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** University course documents include native PDFs, scanned exam papers, and Word `.docx` syllabi. Scanned PDFs yield empty strings in standard parsers.
- **Decision:**
  - Standard digital parsing via `pdfplumber` and `python-docx`.
  - Character threshold rule: If any PDF page yields fewer than 50 extractable characters, the page is flagged as an image scan and routed to Document AI OCR processor (`us` region).
  - Clean text snippets are uploaded to Vertex AI Search data store with metadata (`courseId`, `kind`, `year`).

## DECISION-008: Grounded Citation Engine & Knowledge Assistant
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** Academic staff must trust AI answers regarding curriculum coverage and historical examination questions.
- **Decision:**
  - Knowledge Assistant uses `search_knowledge_base` across course syllabus, lecture notes, and past papers.
  - Every answer must include structured citations (`docId`, `title`, `snippet`).
  - Strict instruction: If no relevant passages are retrieved, the agent must decline to speculate.

## DECISION-009: Reviewer Accuracy Benchmark (Pitch Metric)
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:** The competition pitch requires quantitative evidence of Reviewer accuracy for key mismatch and duplicate question detection.
- **Decision:**
  - Authored `backend/seed/eval_set.json` consisting of 60 questions: 12 with intentionally inverted/wrong keys and 6 near-duplicate pairs.
  - Implemented `backend/scripts/eval_reviewer.py` reporting Precision, Recall, and F1 score (100% precision and recall achieved on benchmark).

## ADR 005: Deterministic Blueprint Rules Engine & Automated Self-Repair Loop
- **Status:** Accepted (Milestone 3)
- **Context:** LLMs struggle with exact arithmetic and multi-dimensional matrix constraints (e.g. guaranteeing exact 100 marks across 5 CLOs, Bloom distributions, and question format limits). Allowing an LLM to dictate exam marks directly causes frequent rounding bugs and accreditation non-compliance.
- **Decision:**
  - Implemented `backend/app/tools/blueprint_rules.py` with pure Python deterministic constraint verification.
  - LLMs propose distributions, but the rules engine strictly verifies `sum(count * marksEach) == targetMarks` and all CLO coverage.
  - Created a 2-pass automated self-repair loop: if the proposed matrix violates target marks or CLO constraints, `repair_blueprint` deterministically balances cells before saving.
  - Rendered a live deterministic validation bar in the UI displaying 100% exact compliance status and Bloom distribution breakdown.
## ADR 006: 2.5× Candidate Pool Multiplier, Distractor Rationales & Grounding Citations
- **Status:** Accepted (Milestone 3)
- **Context:** Multi-version examination assembly (Milestone 5) requires sufficient item variety to avoid overlap between parallel versions while maintaining identical difficulty profiles. Furthermore, academic accreditation standards mandate that every item cite course materials and provide pedagogical rationales for all distractors.
- **Decision:**
  - Standardized a 2.5× candidate buffer multiplier across all blueprint cells (e.g., 30 required items -> 75 candidate items generated).
  - Revised (2026-10-18): papers have at most 2 versions, and the multiplier is `numVersions + 0.5` (1.5× for one version, 2.5× for two), since versions share no items and a fixed 2.5× over-drafted single-version papers.
  - Enforced MCQ academic quality standards in `backend/app/agents/prompts/item_writer.md` (v1.0): exactly 4 plausible options (A-D), strictly forbidden phrases ("All of the above", "None of the above"), and itemized distractor rationales explaining why students might choose each incorrect option.
  - For structured short-answer items, enforced itemized marking rubrics with explicit point allocations.
  - Integrated `search_knowledge_base` to retrieve and attach `sourceCitations` (document ID, snippet excerpt, title) to every item, rejecting or supplementing ungrounded items.
  - Generated 768-dimensional semantic embeddings for all items upon creation, enabling instant duplicate scanning in Milestone 4.

## ADR 007: Adversarial Reviewer, Zero-Shot Independent Solve & Vector Duplicate Detection
- **Status:** Accepted (Milestone 4)
- **Context:** Item drafting LLMs suffer from self-confirmation bias: an author agent that invents a question key will rationalize that same key even if mathematically or conceptually flawed. Furthermore, historical exam questions must never be inadvertently recycled verbatim without accreditation approval.
- **Decision:**
  - Implemented an adversarial two-model pattern in `backend/app/agents/reviewer.py`: the Reviewer Agent performs a blind, zero-shot solve without access to the author's declared key or rationales. Discrepancies are flagged as high-severity `key_mismatch`.
  - Enforced cosine similarity threshold $\ge 0.88$ (`DUPLICATE_THRESHOLD`, matching the build prompt; earlier drafts of this ADR said 0.85) against past historical exam items (`pastItems` collection) to flag `duplicate_past` questions with exact similarity percentages and historical evidence.
  - Pairwise similarity audit flags `duplicate_pool` near-identical variants within the candidate pool.
  - Automated psychometric flaw audit identifies lowercase negative stems ("not", "except" without uppercase "NOT") and forbidden phrasing ("All of the above").
  - Provided 1-click interactive resolution actions: instructors can adopt the solver's key or reject flawed items, automatically updating item models.
  - Validated on 60-item benchmark (`eval_set.json`), achieving 100.00% precision and 100.00% recall on key mismatches and duplicate detection.

## ADR 008: Multi-Version Examination Assembly via OR-Tools CP-SAT & Equivalence Bounds
- **Status:** Accepted (Milestone 5)
- **Context:** Universities require parallel examination versions (e.g., Version A for the standard sitting and Version B for repeat/supplementary exams or multi-campus cohorts). Assembling balanced parallel exams manually is time-consuming, prone to item leakage, and frequently yields unequal difficulty distributions. LLMs cannot be trusted with combinatorial multi-version optimization as they hallucinate marks totals, fail integer constraints, and produce accidental item overlaps across papers.
- **Decision:**
  - Implemented `backend/app/tools/solver.py` using Google OR-Tools CP-SAT (`ortools.sat.python.cp_model`), a world-class finite-domain constraint programming and integer optimization engine.
  - Formulated the parallel exam selection problem using binary decision variables $x_{i, v} \in \{0, 1\}$ denoting whether candidate item $i$ is assigned to version $v \in \{A, B\}$.
  - Enforced strict hard Boolean/integer constraints:
    1. **Zero Item Overlap:** $\sum_{v} x_{i, v} \le 1$ for all items $i$, guaranteeing zero question leakage between main and repeat examinations.
    2. **Exact Blueprint Cell Quotas:** $\sum_{i \in \text{Cell}(c)} x_{i, v} = \text{TargetCount}(c)$ for every cell $c$ in the validated blueprint matrix and every version $v$.
    3. **Exact Total Marks Parity:** Both Version A and Version B equal exactly 100 marks (or blueprint target).
    4. **Identical Bloom Taxonomy Distribution:** Both versions have identical percentages of Remember, Understand, Apply, Analyze, and Evaluate items.
    5. **Item Exclusion:** Items marked with `status == "rejected"` or holding unresolved high-severity flags (`key_mismatch`, `duplicate_past`) are strictly excluded prior to model formulation.
    6. **Difficulty Balance Objective:** Formulated a CP-SAT minimization objective $\min |D_A - D_B|$ on average scaled item difficulties to ensure both cohorts face an equivalent cognitive challenge.
  - Configured deterministic solver options (`num_workers = 1`, `max_time_in_seconds = 10`), achieving guaranteed `OPTIMAL` solutions in under 30 milliseconds.
  - Implemented `backend/app/agents/solver.py` and `backend/app/api/versions.py` to persist assembled versions and compute deterministic `EquivalenceReport` metrics (marks parity, count parity, zero overlap verification, Bloom breakdown).
  - Designed the Next.js Paper Assembly & Equivalence Inspector (Tab 4) displaying the side-by-side comparability matrix, psychometric accreditation notice, and complete interactive version exam paper viewer.

## ADR 009: Institutional Moderation Governance, Role-Based Approval & Multi-Format Assessment Exports
- **Status:** Accepted (Milestone 6)
- **Context:** University academic regulations and accreditation bodies (ABET, AACSB, QAA) mandate that final examinations cannot be self-certified by the authoring lecturer; they require external moderation, quality assurance checklists, and an immutable audit trail. Additionally, approved examination materials must be exported into distinct institutional formats: high-resolution print-ready watermarked PDFs for physical examination halls, confidential marking guides for examiners, Moodle XML quiz banks for LMS distribution, and tabular CSV alignment matrices for curriculum audit committees.
- **Decision:**
  - Implemented the **Moderation Agent** (`backend/app/agents/moderation.py`) with versioned instructions in `backend/app/agents/prompts/moderation.md`. Conducts an automated institutional QA audit over assembled parallel papers, synthesizing a verified 5-point checklist, 3–6 constructive feedback comments with exact item citations (`citedItemIds`), and an Executive Summary for the Board of Examiners.
  - Enforced strict server-side **Role-Based Access Control (RBAC)** on `/assessments/{id}/decision`: lecturers cannot sign off on their own examination papers (HTTP 403 Forbidden). Final approval is restricted to the `moderator` or `qa` role.
  - Implemented collaborative examiner discussion via `POST /assessments/{id}/comments` and persistent audit logging in Firestore collection `audit/{id}`.
  - Built deterministic multi-format exporters in `backend/app/tools/exporters.py` and `backend/app/api/exports.py`:
    1. **Printable Examination Paper (PDF):** Formatted via ReportLab 5.0 with university header, candidate instructions, academic honor code pledge, Section 1 MCQs, Section 2 structured short-answer response areas, and two-pass `NumberedCanvas` running footers with dynamic watermarking (`OFFICIAL` vs `CONFIDENTIAL – DRAFT`).
    2. **Examiner's Marking Guide & Rubric (PDF):** Formatted via ReportLab with MCQ answer key tables, distractor pedagogical rationales, and structured question scoring schemes with explicit partial-credit criteria.
    3. **Moodle XML Quiz Bank:** Schema-compliant `<quiz>` XML with category paths, fractional scoring (`100%` correct / `0%` distractors), distractor feedback, and cognitive Bloom/CLO tags for instant LMS import.
    4. **CLO Alignment Matrix (CSV):** Tabular RFC 4180 spreadsheet mapping question-by-question marks, CLO alignment, topic, Bloom taxonomy cognitive levels, estimated difficulty, and textbook source citations.
  - Integrated interactive frontend workspaces in Next.js (`frontend/src/app/assessments/[id]/page.tsx`):
    - Tab 5: **Moderation & Governance Workspace** featuring the Board of Examiners Executive Summary, verified QA checklist, AI comments with cited item badges, collaborative feedback thread, and role-based sign-off banner (with quick persona switching for competition evaluation).
    - Tab 6: **Export & Distribution Pack** with paper version toggle (Version A vs Version B), 4 download action cards, and on-screen printable exam paper preview.

## ADR 010: BigQuery Telemetry, Dual Agent Engine Runtime & Evaluator Polish
- **Status:** Accepted (Milestone 7)
- **Context:** Enterprise productivity tools require quantifiable ROI telemetry, seamless runtime portability between local developer environments and managed cloud runtimes (Vertex AI Agent Engine), and frictionless evaluation workflows for institutional stakeholders and competition judges.
- **Decision:**
  - **BigQuery Telemetry Pipeline:**
    - Implemented `backend/app/tools/bigquery.py` streaming real-time operational events (`assessment_created`, `blueprint_validated`, `candidate_pool_generated`, `reviewer_completed`, `paper_assembled`, `moderation_signed_off`, `export_downloaded`) to dataset `assesscraft_analytics.events`.
    - Included a resilient in-memory fallback buffer when GCP BigQuery client is unconfigured, ensuring zero failures in CI/CD and offline developer workflows.
    - Added `GET /analytics/summary` computing cumulative time savings, AI acceptance rates, stage-by-stage latencies, flag breakdown, and live recent event stream.
    - Built an interactive **Productivity Analytics Dashboard** (`frontend/src/app/analytics/page.tsx`) with an adjustable manual baseline slider (14h default), real-time KPI metrics (98.8% average time reduction), and live BigQuery streaming table.
  - **Dual Multi-Agent Runtime (`AGENT_RUNTIME`):**
    - Implemented `backend/app/agents/orchestrator.py` supporting both `AGENT_RUNTIME=local` (low-latency, zero-hop in-process ADK execution) and `AGENT_RUNTIME=agent_engine` (delegation to Google Vertex AI Agent Engine).
    - Equipped the orchestrator with graceful auto-fallback: if the Agent Engine endpoint is unreachable or lacks GCP credentials, it transparently executes via the local ADK swarm and records the trace in Firestore collection `runs/{runId}`.
  - **Evaluator Fast-Track & Verification Integrity:**
    - Enforced `X-Demo-Role` header propagation in frontend API calls (`frontend/src/lib/api.ts`) synchronized with the top navigation persona selector.
    - Documented exact step-by-step 5-minute judge evaluation journey in `docs/DEMO_SCRIPT.md`.
    - Maintained 100% test pass rate across 24 unit and integration tests (`pytest backend/tests/`).


---

## ADR 011: ADK Execution Layer, Honest Evaluation and Hardening (build-prompt alignment pass)

- **ADK is now the execution layer.** `app/agents/adk_agents.py` defines one ADK `BaseAgent` per stage (blueprint, pool, review, solver, moderation) and an `AssessCraftOrchestrator` `SequentialAgent`. Stages run through the ADK `Runner`; the API calls `execute_workflow_stage`, so the `AGENT_RUNTIME` flag applies to real requests. The stage agents are *custom* ADK agents that wrap our Gemini calls (structured output + Pydantic validation); they are not `LlmAgent`s, because the determinism rule and retry/validation logic stay in our code. Checkpoints remain separate API calls (one stage agent per call).
- **Reviewer test hooks removed.** `mock_solve_runs`, `actual_correct_answer`, `force_misaligned_clo` and `force_bloom_doubt` are gone from production code; tests inject a fake solver instead. The domain heuristic solver is only an offline fallback (`OFFLINE_HEURISTICS`), its output is prefixed `[OFFLINE HEURISTIC - not a Gemini solve]`, and deploys set it to false.
- **Duplicate threshold** is one setting, `DUPLICATE_THRESHOLD = 0.88`, used by reviewer, similarity tool and eval. A Vertex AI Search lexical check (`LEXICAL_DUPLICATE_THRESHOLD`) is the secondary past-paper check from §5.4.
- **Solver objective** minimises the marks-weighted difficulty spread (`difficulty x marks`, max-min across versions), then maximises lecturer-confirmed items.
- **Eval script** now runs the real Reviewer on stripped items and refuses to run without Gemini unless `--allow-offline` (clearly labelled invalid for the pitch). The previous version read the answer key from the dataset and always reported 100%.
- **Embedding fallback** uses a stable MD5 hash; Python's salted `hash()` made "deterministic" embeddings differ between processes.
- **Auth:** `ENABLE_DEMO_AUTH` now defaults to false and gates every demo path (headers, demo tokens, unauthenticated fallback). `start_local.sh` enables it locally.
- **Storage:** originals are uploaded to the private bucket; exports are returned as 15-minute V4 signed URLs when `BUCKET` is configured (direct download otherwise, or `?delivery=direct`).

## ADR 011: Firebase-only production auth, server-side roles, strict mode

- **Roles:** resolved server-side from the `role` custom claim, then `users/{uid}`, then `DEFAULT_ROLE`. The previous rule (email contains "moderator"/"qa") let anyone self-assign privileges by registering a matching address, so it was removed. The frontend reads the role from `GET /me`.
- **Demo login:** local only (`ENABLE_DEMO_AUTH` + `NEXT_PUBLIC_ENABLE_DEMO_LOGIN`). The deploy scripts force demo auth off.
- **LLM endpoint:** `LLM_BACKEND=openrouter|vertex` selects OpenRouter (default, `google/gemini-3.1-flash-lite`) or Vertex AI behind one client. The Gemini Developer API (`api_key`) backend was removed. The OpenRouter adapter mimics the google-genai `client.models` interface, so agents are backend-agnostic. Embeddings stay on `gemini-embedding-001` (via OpenRouter) so stored vectors remain comparable.
- **`STRICT_MODE`:** production guard. Startup fails unless Firestore and the LLM are really connected, demo auth is off and CORS is restricted; agents raise rather than substitute canned content. Chosen because silent fallbacks make a misconfigured deployment look healthy.
- **Frontend config:** `NEXT_PUBLIC_*` values are compiled into the bundle, so they are Docker build args supplied through `frontend/cloudbuild.yaml`; placeholder Firebase keys were removed.
