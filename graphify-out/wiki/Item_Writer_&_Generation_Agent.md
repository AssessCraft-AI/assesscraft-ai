# Item Writer & Generation Agent

> 83 nodes · cohesion 0.06

## Key Concepts

- **log_event()** (38 connections) — `backend/app/tools/events.py`
- **item_writer.py** (36 connections) — `backend/app/agents/item_writer.py`
- **agents/moderation.py** (28 connections) — `backend/app/agents/moderation.py`
- **reviewer.py** (28 connections) — `backend/app/agents/reviewer.py`
- **api/moderation.py** (27 connections) — `backend/app/api/moderation.py`
- **events.py** (27 connections) — `backend/app/tools/events.py`
- **generate_id()** (26 connections) — `backend/app/models.py`
- **run_item_writer_agent()** (23 connections) — `backend/app/agents/item_writer.py`
- **traces.py** (23 connections) — `backend/app/services/traces.py`
- **run_moderation_agent()** (22 connections) — `backend/app/agents/moderation.py`
- **orchestrator.py** (22 connections) — `backend/app/agents/orchestrator.py`
- **config.py** (18 connections) — `backend/app/config.py`
- **time** (18 connections)
- **current_time_iso()** (17 connections) — `backend/app/models.py`
- **execute_workflow_stage()** (16 connections) — `backend/app/agents/orchestrator.py`
- **test_milestone7.py** (16 connections) — `backend/tests/test_milestone7.py`
- **get_genai_client()** (14 connections) — `backend/app/tools/similarity.py`
- **json** (13 connections)
- **submit_moderation_decision()** (11 connections) — `backend/app/api/moderation.py`
- **upload_document()** (10 connections) — `backend/app/api/documents.py`
- **add_moderation_comment()** (10 connections) — `backend/app/api/moderation.py`
- **Comment** (8 connections) — `backend/app/models.py`
- **ModerationRecord** (8 connections) — `backend/app/models.py`
- **RunTrace** (8 connections) — `backend/app/models.py`
- **pydantic** (8 connections)
- *... and 58 more nodes in this community*

## Relationships

- [Backend API & Analytics](Backend_API_&_Analytics.md) (103 shared connections)
- [Blueprint Agent & Workflow](Blueprint_Agent_&_Workflow.md) (62 shared connections)
- [Exam Solver & OR-Tools CP-SAT](Exam_Solver_&_OR-Tools_CP-SAT.md) (30 shared connections)
- [Grounded Assistant Agent](Grounded_Assistant_Agent.md) (15 shared connections)
- [Export & PDF Rendering Tools](Export_&_PDF_Rendering_Tools.md) (5 shared connections)
- [Item Writer Cognitive Prompts](Item_Writer_Cognitive_Prompts.md) (1 shared connections)
- [Moderation Agent Prompts](Moderation_Agent_Prompts.md) (1 shared connections)
- [Adversarial Reviewer Prompts](Adversarial_Reviewer_Prompts.md) (1 shared connections)
- [Document Intelligence Prompts](Document_Intelligence_Prompts.md) (1 shared connections)

## Source Files

- `backend/app/agents/item_writer.py`
- `backend/app/agents/moderation.py`
- `backend/app/agents/orchestrator.py`
- `backend/app/agents/reviewer.py`
- `backend/app/api/documents.py`
- `backend/app/api/moderation.py`
- `backend/app/config.py`
- `backend/app/models.py`
- `backend/app/services/traces.py`
- `backend/app/tools/events.py`
- `backend/app/tools/similarity.py`
- `backend/tests/test_milestone7.py`

## Audit Trail

- EXTRACTED: 399 (95%)
- INFERRED: 21 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*