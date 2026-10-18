# run_blueprint_agent()

> God node · 22 connections · `backend/app/agents/blueprint.py`

**Community:** [Blueprint Agent & Workflow](Blueprint_Agent_&_Workflow.md)

## Connections by Relation

### calls
- [run_item_writer_agent()](run_item_writer_agent.md) `EXTRACTED`
- [seed_database()](seed_database.md) `EXTRACTED`
- CLO `EXTRACTED`
- Topic `EXTRACTED`
- time `EXTRACTED`
- execute_workflow_stage() `EXTRACTED`
- Blueprint `EXTRACTED`
- get_genai_client() `EXTRACTED`
- json `EXTRACTED`
- BlueprintCell `EXTRACTED`
- validate_blueprint() `EXTRACTED`
- repair_blueprint() `EXTRACTED`
- test_item_writer_agent_and_grounding() `EXTRACTED`
- test_blueprint_agent_and_rules() `EXTRACTED`

### contains
- blueprint.py `EXTRACTED`

### imports
- item_writer.py `EXTRACTED`
- load_seed.py `EXTRACTED`
- orchestrator.py `EXTRACTED`
- blueprints.py `EXTRACTED`
- test_milestone3.py `EXTRACTED`

### indirect_call
- generate_blueprint() `INFERRED`

### rationale_for
- Executes the Blueprint Agent: 1. Reads assessment requirements, course CLOs and… `EXTRACTED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*