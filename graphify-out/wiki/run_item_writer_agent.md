# run_item_writer_agent()

> God node · 23 connections · `backend/app/agents/item_writer.py`

**Community:** [Item Writer & Generation Agent](Item_Writer_&_Generation_Agent.md)

## Connections by Relation

### calls
- [log_event()](log_event.md) `EXTRACTED`
- [Item](Item.md) `EXTRACTED`
- [run_blueprint_agent()](run_blueprint_agent.md) `EXTRACTED`
- [seed_database()](seed_database.md) `EXTRACTED`
- compute_embedding() `EXTRACTED`
- time `EXTRACTED`
- execute_workflow_stage() `EXTRACTED`
- Blueprint `EXTRACTED`
- get_genai_client() `EXTRACTED`
- json `EXTRACTED`
- SourceCitation `EXTRACTED`
- search_knowledge_base() `EXTRACTED`
- Option `EXTRACTED`
- test_item_writer_agent_and_grounding() `EXTRACTED`
- uuid `EXTRACTED`
- math `EXTRACTED`

### contains
- item_writer.py `EXTRACTED`

### imports
- load_seed.py `EXTRACTED`
- orchestrator.py `EXTRACTED`
- items.py `EXTRACTED`
- test_milestone3.py `EXTRACTED`

### indirect_call
- generate_item_pool() `INFERRED`

### rationale_for
- Executes the Item Writer Agent: 1. Loads assessment and blueprint cells. 2.… `EXTRACTED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*