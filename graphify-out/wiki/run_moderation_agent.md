# run_moderation_agent()

> God node · 22 connections · `backend/app/agents/moderation.py`

**Community:** [Item Writer & Generation Agent](Item_Writer_&_Generation_Agent.md)

## Connections by Relation

### calls
- [log_event()](log_event.md) `EXTRACTED`
- [generate_id()](generate_id.md) `EXTRACTED`
- [seed_database()](seed_database.md) `EXTRACTED`
- time `EXTRACTED`
- current_time_iso() `EXTRACTED`
- execute_workflow_stage() `EXTRACTED`
- get_genai_client() `EXTRACTED`
- submit_moderation_decision() `EXTRACTED`
- add_moderation_comment() `EXTRACTED`
- Comment `EXTRACTED`
- ModerationRecord `EXTRACTED`
- ModerationItem `EXTRACTED`
- ModerationAgentOutput `EXTRACTED`
- generate_moderation_pack() `EXTRACTED`
- get_moderation_record() `EXTRACTED`
- test_moderation_agent_generation() `EXTRACTED`

### contains
- agents/moderation.py `EXTRACTED`

### imports
- api/moderation.py `EXTRACTED`
- load_seed.py `EXTRACTED`
- orchestrator.py `EXTRACTED`
- test_milestone6.py `EXTRACTED`

### rationale_for
- Moderation Agent: Performs comprehensive academic quality assurance,… `EXTRACTED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*