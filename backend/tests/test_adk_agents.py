"""The agent swarm runs on Google ADK: stage agents + SequentialAgent orchestrator via the ADK Runner."""
import pytest
from google.adk.agents import BaseAgent, SequentialAgent

from app.agents import adk_agents
from app.agents.adk_agents import STAGES, build_orchestrator, run_pipeline_with_adk, run_stage_with_adk
from seed.load_seed import seed_database


@pytest.fixture(autouse=True)
async def setup_seed_data():
    await seed_database()


def test_orchestrator_is_an_adk_sequential_agent_over_all_stages():
    orchestrator = build_orchestrator()
    assert isinstance(orchestrator, SequentialAgent)
    assert [a.stage for a in orchestrator.sub_agents] == STAGES
    assert all(isinstance(a, BaseAgent) for a in orchestrator.sub_agents)


@pytest.mark.asyncio
async def test_single_stage_runs_through_adk_runner():
    out = await run_stage_with_adk("solver", "asm-demo", "run-adk-stage")
    assert out["versionCount"] == 2
    assert out["solverStatus"] == "OPTIMAL"


@pytest.mark.asyncio
async def test_pipeline_runs_stages_in_order_via_sequential_agent(monkeypatch):
    calls = []

    async def fake_stage(stage, assessment_id, run_id):
        calls.append(stage)
        return {"stage": stage}

    monkeypatch.setattr(adk_agents, "run_stage_impl", fake_stage)
    results = await run_pipeline_with_adk("asm-demo", "run-adk-pipeline")

    assert calls == STAGES
    assert list(results) == STAGES


@pytest.mark.asyncio
async def test_unknown_stage_is_rejected():
    with pytest.raises(ValueError):
        await run_stage_with_adk("nope", "asm-demo", "run-x")
