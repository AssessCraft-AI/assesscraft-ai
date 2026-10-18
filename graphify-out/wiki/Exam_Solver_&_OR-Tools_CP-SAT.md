# Exam Solver & OR-Tools CP-SAT

> 31 nodes · cohesion 0.14

## Key Concepts

- **BaseModel** (27 connections)
- **Item** (23 connections) — `backend/app/models.py`
- **test_milestone5.py** (23 connections) — `backend/tests/test_milestone5.py`
- **agents/solver.py** (21 connections) — `backend/app/agents/solver.py`
- **run_solver_agent()** (17 connections) — `backend/app/agents/solver.py`
- **Blueprint** (15 connections) — `backend/app/models.py`
- **tools/solver.py** (15 connections) — `backend/app/tools/solver.py`
- **Flag** (12 connections) — `backend/app/models.py`
- **assemble_paper_versions()** (12 connections) — `backend/app/tools/solver.py`
- **EquivalenceReport** (8 connections) — `backend/app/models.py`
- **Option** (8 connections) — `backend/app/models.py`
- **PaperVersion** (8 connections) — `backend/app/models.py`
- **create_mock_blueprint_and_pool()** (8 connections) — `backend/tests/test_milestone5.py`
- **Multi-Version Paper Assembly Solver Documentation (v1.0)** (6 connections) — `backend/app/agents/prompts/solver.md`
- **check_item_quality_flaws()** (6 connections) — `backend/app/agents/reviewer.py`
- **trigger_assembly()** (5 connections) — `backend/app/api/versions.py`
- **test_solver_agent_and_api_workflow()** (5 connections) — `backend/tests/test_milestone5.py`
- **test_ortools_cp_sat_assembly_zero_overlap()** (3 connections) — `backend/tests/test_milestone5.py`
- **test_ortools_exclusion_of_rejected_items()** (3 connections) — `backend/tests/test_milestone5.py`
- **Academic Equivalence Bounds** (1 connections) — `backend/app/agents/prompts/solver.md`
- **Multi-Version Paper Assembly Solver Documentation (v1.0)** (1 connections) — `backend/app/agents/prompts/solver.md`
- **Objective Function: Difficulty Balance** (1 connections) — `backend/app/agents/prompts/solver.md`
- **Problem Formulation & Constraints** (1 connections) — `backend/app/agents/prompts/solver.md`
- **Strict Optimization Constraints** (1 connections) — `backend/app/agents/prompts/solver.md`
- **Checks for common item writing flaws: - Lowercase negative phrasing ("not",…** (1 connections) — `backend/app/agents/reviewer.py`
- *... and 6 more nodes in this community*

## Relationships

- [Backend API & Analytics](Backend_API_&_Analytics.md) (40 shared connections)
- [Item Writer & Generation Agent](Item_Writer_&_Generation_Agent.md) (30 shared connections)
- [Blueprint Agent & Workflow](Blueprint_Agent_&_Workflow.md) (30 shared connections)
- [Grounded Assistant Agent](Grounded_Assistant_Agent.md) (3 shared connections)
- [Export & PDF Rendering Tools](Export_&_PDF_Rendering_Tools.md) (2 shared connections)

## Source Files

- `backend/app/agents/prompts/solver.md`
- `backend/app/agents/reviewer.py`
- `backend/app/agents/solver.py`
- `backend/app/api/versions.py`
- `backend/app/models.py`
- `backend/app/tools/solver.py`
- `backend/tests/test_milestone5.py`

## Audit Trail

- EXTRACTED: 148 (87%)
- INFERRED: 23 (13%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*