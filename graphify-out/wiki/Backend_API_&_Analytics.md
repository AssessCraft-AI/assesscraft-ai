# Backend API & Analytics

> 96 nodes · cohesion 0.06

## Key Concepts

- **models.py** (64 connections) — `backend/app/models.py`
- **User** (48 connections) — `backend/app/models.py`
- **main.py** (37 connections) — `backend/app/main.py`
- **firestore.py** (34 connections) — `backend/app/services/firestore.py`
- **typing** (31 connections)
- **versions.py** (23 connections) — `backend/app/api/versions.py`
- **log_audit()** (23 connections) — `backend/app/services/audit.py`
- **flags.py** (22 connections) — `backend/app/api/flags.py`
- **courses.py** (21 connections) — `backend/app/api/courses.py`
- **documents.py** (21 connections) — `backend/app/api/documents.py`
- **items.py** (21 connections) — `backend/app/api/items.py`
- **auth.py** (21 connections) — `backend/app/auth.py`
- **assessments.py** (20 connections) — `backend/app/api/assessments.py`
- **blueprints.py** (20 connections) — `backend/app/api/blueprints.py`
- **exports.py** (16 connections) — `backend/app/api/exports.py`
- **audit.py** (16 connections) — `backend/app/services/audit.py`
- **get_current_user()** (15 connections) — `backend/app/auth.py`
- **FastAPI** (15 connections)
- **api/assistant.py** (14 connections) — `backend/app/api/assistant.py`
- **require_role()** (13 connections) — `backend/app/auth.py`
- **analytics.py** (10 connections) — `backend/app/api/analytics.py`
- **runs.py** (9 connections) — `backend/app/api/runs.py`
- **create_assessment()** (8 connections) — `backend/app/api/assessments.py`
- **export_assessment()** (8 connections) — `backend/app/api/exports.py`
- **resolve_flag()** (8 connections) — `backend/app/api/flags.py`
- *... and 71 more nodes in this community*

## Relationships

- [Item Writer & Generation Agent](Item_Writer_&_Generation_Agent.md) (103 shared connections)
- [Blueprint Agent & Workflow](Blueprint_Agent_&_Workflow.md) (54 shared connections)
- [Exam Solver & OR-Tools CP-SAT](Exam_Solver_&_OR-Tools_CP-SAT.md) (40 shared connections)
- [Grounded Assistant Agent](Grounded_Assistant_Agent.md) (20 shared connections)
- [Export & PDF Rendering Tools](Export_&_PDF_Rendering_Tools.md) (10 shared connections)
- [Document Intelligence Prompts](Document_Intelligence_Prompts.md) (2 shared connections)
- [FastAPI Middleware & Telemetry](FastAPI_Middleware_&_Telemetry.md) (1 shared connections)
- [Firestore Persistence Service](Firestore_Persistence_Service.md) (1 shared connections)

## Source Files

- `backend/app/api/analytics.py`
- `backend/app/api/assessments.py`
- `backend/app/api/assistant.py`
- `backend/app/api/blueprints.py`
- `backend/app/api/courses.py`
- `backend/app/api/documents.py`
- `backend/app/api/exports.py`
- `backend/app/api/flags.py`
- `backend/app/api/items.py`
- `backend/app/api/runs.py`
- `backend/app/api/versions.py`
- `backend/app/auth.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/services/audit.py`
- `backend/app/services/firestore.py`
- `backend/app/tools/exporters.py`

## Audit Trail

- EXTRACTED: 424 (88%)
- INFERRED: 59 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*