"""
Google ADK wiring for the AssessCraft agent swarm (Build Prompt §2, §5).

Each pipeline stage is an ADK custom agent (``BaseAgent``) that delegates to the
existing LLM-backed stage function (structured output, Pydantic validation,
trace recording). The ``AssessCraftOrchestrator`` is an ADK ``SequentialAgent``
over those stage agents, and all execution goes through the ADK ``Runner``.

Human checkpoints are separate API calls: the API runs ONE stage agent per call
(``run_stage_with_adk``); only the full-pipeline path runs the SequentialAgent.
"""
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.blueprint import run_blueprint_agent
from app.agents.item_writer import run_item_writer_agent
from app.agents.moderation import run_moderation_agent
from app.agents.reviewer import run_reviewer_agent
from app.agents.solver import run_solver_agent

logger = logging.getLogger("assesscraft.adk")

APP_NAME = "assesscraft"
STAGES: List[str] = ["blueprint", "pool", "review", "solver", "moderation"]


async def run_stage_impl(stage: str, assessment_id: str, run_id: str) -> Dict[str, Any]:
    """Runs one stage's LLM-backed agent and returns a small JSON-safe summary."""
    if stage == "blueprint":
        bp = await run_blueprint_agent(assessment_id, run_id=run_id)
        return {"valid": bp.valid, "cellCount": len(bp.cells), "totals": bp.totals}
    if stage == "pool":
        items = await run_item_writer_agent(assessment_id, run_id=run_id)
        return {"itemCount": len(items)}
    if stage == "review":
        flags = await run_reviewer_agent(assessment_id, run_id=run_id)
        return {"flagsCount": len(flags)}
    if stage == "solver":
        versions, eq = await run_solver_agent(assessment_id, run_id=run_id)
        return {"versionCount": len(versions), "solverStatus": eq.solverStatus}
    if stage == "moderation":
        mod = await run_moderation_agent(assessment_id, run_id=run_id)
        return {"checklistCount": len(mod.checklist), "decision": mod.decision}
    raise ValueError(f"Unknown workflow stage: {stage}")


class StageAgent(BaseAgent):
    """ADK agent wrapping one pipeline stage. Reads ids from session state."""

    stage: str

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        output = await run_stage_impl(self.stage, state["assessment_id"], state["run_id"])
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(role="model", parts=[types.Part(text=f"{self.stage}: {output}")]),
            actions=EventActions(state_delta={f"result_{self.stage}": output}),
        )


def _build_stage_agent(stage: str) -> StageAgent:
    return StageAgent(
        name=f"{stage.capitalize()}Agent",
        description=f"AssessCraft '{stage}' stage agent",
        stage=stage,
    )


STAGE_AGENTS: Dict[str, StageAgent] = {s: _build_stage_agent(s) for s in STAGES}


def build_orchestrator() -> SequentialAgent:
    """Orchestrator: blueprint -> pool -> review -> solver -> moderation (SequentialAgent)."""
    return SequentialAgent(
        name="AssessCraftOrchestrator",
        description="Coordinates the AssessCraft stage agents end to end.",
        sub_agents=[_build_stage_agent(s) for s in STAGES],
    )


async def _run_with_runner(agent: BaseAgent, assessment_id: str, run_id: str) -> Dict[str, Any]:
    """Runs an ADK agent through the Runner; returns the collected ``result_*`` state deltas."""
    session_service = InMemorySessionService()
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id="system",
        session_id=f"{run_id}-{uuid.uuid4().hex[:8]}",
        state={"assessment_id": assessment_id, "run_id": run_id},
    )
    results: Dict[str, Any] = {}
    message = types.Content(role="user", parts=[types.Part(text="execute")])
    async for event in runner.run_async(user_id="system", session_id=session.id, new_message=message):
        for key, value in (event.actions.state_delta or {}).items():
            if key.startswith("result_"):
                results[key[len("result_"):]] = value
    return results


async def run_stage_with_adk(stage: str, assessment_id: str, run_id: str) -> Dict[str, Any]:
    """Runs a single stage agent via the ADK Runner (one human-checkpoint step)."""
    if stage not in STAGE_AGENTS:
        raise ValueError(f"Unknown workflow stage: {stage}")
    results = await _run_with_runner(STAGE_AGENTS[stage], assessment_id, run_id)
    return results[stage]


async def run_pipeline_with_adk(assessment_id: str, run_id: str) -> Dict[str, Dict[str, Any]]:
    """Runs the full SequentialAgent orchestrator via the ADK Runner."""
    return await _run_with_runner(build_orchestrator(), assessment_id, run_id)
