# Blueprint Agent & Workflow

> 66 nodes · cohesion 0.08

## Key Concepts

- **blueprint.py** (26 connections) — `backend/app/agents/blueprint.py`
- **load_seed.py** (25 connections) — `backend/seed/load_seed.py`
- **Assessment** (23 connections) — `backend/app/models.py`
- **run_blueprint_agent()** (22 connections) — `backend/app/agents/blueprint.py`
- **seed_database()** (22 connections) — `backend/seed/load_seed.py`
- **run_reviewer_agent()** (20 connections) — `backend/app/agents/reviewer.py`
- **CLO** (20 connections) — `backend/app/models.py`
- **Topic** (20 connections) — `backend/app/models.py`
- **test_milestone3.py** (20 connections) — `backend/tests/test_milestone3.py`
- **test_milestone4.py** (20 connections) — `backend/tests/test_milestone4.py`
- **Course** (19 connections) — `backend/app/models.py`
- **compute_embedding()** (19 connections) — `backend/app/tools/similarity.py`
- **doc_intel.py** (18 connections) — `backend/app/agents/doc_intel.py`
- **similarity.py** (18 connections) — `backend/app/tools/similarity.py`
- **BlueprintCell** (12 connections) — `backend/app/models.py`
- **run_doc_intel_extraction()** (11 connections) — `backend/app/agents/doc_intel.py`
- **blueprint_rules.py** (9 connections) — `backend/app/tools/blueprint_rules.py`
- **validate_blueprint()** (9 connections) — `backend/app/tools/blueprint_rules.py`
- **repair_blueprint()** (8 connections) — `backend/app/tools/blueprint_rules.py`
- **Document** (7 connections) — `backend/app/models.py`
- **cosine_similarity()** (7 connections) — `backend/app/tools/similarity.py`
- **eval_reviewer.py** (7 connections) — `backend/scripts/eval_reviewer.py`
- **setup_test_data()** (7 connections) — `backend/tests/test_milestone4.py`
- **test_reviewer_key_mismatch_and_flaw_detection()** (7 connections) — `backend/tests/test_milestone4.py`
- **PastItem** (6 connections) — `backend/app/models.py`
- *... and 41 more nodes in this community*

## Relationships

- [Item Writer & Generation Agent](Item_Writer_&_Generation_Agent.md) (62 shared connections)
- [Backend API & Analytics](Backend_API_&_Analytics.md) (54 shared connections)
- [Exam Solver & OR-Tools CP-SAT](Exam_Solver_&_OR-Tools_CP-SAT.md) (30 shared connections)
- [Grounded Assistant Agent](Grounded_Assistant_Agent.md) (8 shared connections)
- [Export & PDF Rendering Tools](Export_&_PDF_Rendering_Tools.md) (7 shared connections)
- [Document Intelligence Prompts](Document_Intelligence_Prompts.md) (2 shared connections)

## Source Files

- `backend/app/agents/blueprint.py`
- `backend/app/agents/doc_intel.py`
- `backend/app/agents/prompts/blueprint.md`
- `backend/app/agents/reviewer.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/tools/blueprint_rules.py`
- `backend/app/tools/similarity.py`
- `backend/scripts/eval_reviewer.py`
- `backend/seed/load_seed.py`
- `backend/tests/test_milestone3.py`
- `backend/tests/test_milestone4.py`
- `backend/tests/test_milestone5.py`
- `backend/tests/test_milestone7.py`

## Audit Trail

- EXTRACTED: 284 (88%)
- INFERRED: 40 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*