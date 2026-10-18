# log_event()

> God node · 38 connections · `backend/app/tools/events.py`

**Community:** [Item Writer & Generation Agent](Item_Writer_&_Generation_Agent.md)

## Connections by Relation

### calls
- [generate_id()](generate_id.md) `EXTRACTED`
- [run_item_writer_agent()](run_item_writer_agent.md) `EXTRACTED`
- [run_moderation_agent()](run_moderation_agent.md) `EXTRACTED`
- run_reviewer_agent() `EXTRACTED`
- run_solver_agent() `EXTRACTED`
- current_time_iso() `EXTRACTED`
- execute_workflow_stage() `EXTRACTED`
- submit_moderation_decision() `EXTRACTED`
- upload_document() `EXTRACTED`
- create_assessment() `EXTRACTED`
- export_assessment() `EXTRACTED`
- resolve_flag() `EXTRACTED`
- run_full_assessment_pipeline() `EXTRACTED`
- create_course() `EXTRACTED`
- update_course_outcomes() `EXTRACTED`
- patch_item() `EXTRACTED`
- update_blueprint() `EXTRACTED`
- test_analytics_summary_with_real_events() `EXTRACTED`
- get_bq_client() `EXTRACTED`

### contains
- events.py `EXTRACTED`

### imports
- item_writer.py `EXTRACTED`
- agents/moderation.py `EXTRACTED`
- reviewer.py `EXTRACTED`
- api/moderation.py `EXTRACTED`
- versions.py `EXTRACTED`
- orchestrator.py `EXTRACTED`
- flags.py `EXTRACTED`
- agents/solver.py `EXTRACTED`
- courses.py `EXTRACTED`
- documents.py `EXTRACTED`
- items.py `EXTRACTED`
- assessments.py `EXTRACTED`
- blueprints.py `EXTRACTED`
- exports.py `EXTRACTED`
- test_milestone7.py `EXTRACTED`

### indirect_call
- _insert() `INFERRED`

### rationale_for
- Emits a structured telemetry event to BigQuery and in-memory buffer. Fire-and-… `EXTRACTED`

### references
- Any `EXTRACTED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*