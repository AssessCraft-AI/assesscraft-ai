import asyncio
import time
import logging
from typing import Dict, Any, Optional

from app.config import settings
from app.services.traces import tracker
from app.tools.events import log_event
from app.agents.adk_agents import run_stage_with_adk

logger = logging.getLogger("assesscraft.orchestrator")

# Built once per process: connecting fetches the remote engine, too slow to repeat per stage.
_engine_client: Optional["AgentEngineClient"] = None


class AgentEngineClient:
    """
    Client for Vertex AI Reasoning Engines / Agent Engine.
    Enables remote execution of the assessment agent swarm behind the AGENT_RUNTIME flag.
    """

    def __init__(self, project_id: str, region: str, engine_id: Optional[str] = None):
        self.project_id = project_id
        self.region = region
        self.engine_id = engine_id
        self._remote_client = None

        if project_id and engine_id:
            try:
                import vertexai
                from vertexai.preview import reasoning_engines
                vertexai.init(project=project_id, location=region)
                self._remote_client = reasoning_engines.ReasoningEngine(engine_id)
                logger.info(f"Connected to Vertex AI Agent Engine: {engine_id}")
            except Exception as e:
                logger.warning(f"Could not connect to Vertex AI Agent Engine ({e}). Fallback to local ADK.")
                self._remote_client = None

    @property
    def is_connected(self) -> bool:
        return self._remote_client is not None

    async def query(self, prompt: str, **kwargs) -> Any:
        if self._remote_client:
            return await asyncio.to_thread(self._remote_client.query, prompt=prompt, **kwargs)
        raise RuntimeError("Agent Engine client is not initialized or remote runtime is unconfigured.")


async def execute_workflow_stage(
    stage: str,
    assessment_id: str,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a discrete stage of the assessment copilot workflow.
    Routes execution to either local ADK agent swarm or Vertex AI Agent Engine.
    """
    start_time = time.time()
    run_id = run_id or f"run-{assessment_id[:8]}"

    logger.info(
        f"Orchestrator invoking stage '{stage}' for assessment '{assessment_id}' | "
        f"runtime: {settings.AGENT_RUNTIME}"
    )

    # 1. Attempt Vertex AI Agent Engine execution if enabled
    if settings.AGENT_RUNTIME == "agent_engine" and settings.AGENT_ENGINE_ID:
        global _engine_client
        try:
            if _engine_client is None or not _engine_client.is_connected:
                _engine_client = AgentEngineClient(
                    project_id=settings.GCP_PROJECT_ID,
                    region=settings.GCP_REGION,
                    engine_id=settings.AGENT_ENGINE_ID,
                )
            if not _engine_client.is_connected:
                raise RuntimeError(f"Vertex AI Agent Engine {settings.AGENT_ENGINE_ID} is unreachable")
            logger.info(f"Delegating stage '{stage}' to Vertex AI Agent Engine...")
            result = await _engine_client.query(
                prompt=f"Execute assessment workflow stage: {stage}",
                assessment_id=assessment_id,
                run_id=run_id,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            await tracker.record_step(
                run_id=run_id,
                agent="Orchestrator",
                tool="vertex_ai_agent_engine",
                input_summary=f"Remote execution of stage '{stage}' on Vertex AI Agent Engine ({settings.AGENT_ENGINE_ID})",
                output_summary=f"Stage '{stage}' completed remotely in {duration_ms}ms",
                status="completed",
                duration_ms=duration_ms,
            )
            return {"status": "success", "runtime": "agent_engine", "result": result}
        except Exception as e:
            if settings.STRICT_MODE:
                raise  # STRICT_MODE means no silent fallbacks: production must not quietly run locally
            logger.warning(
                f"Vertex AI Agent Engine execution encountered an issue ({e}). "
                "Gracefully falling back to local ADK in-process runtime for demo resilience."
            )

    # 2. Local in-process execution: the stage runs as an ADK agent through the ADK Runner
    stage_output = await run_stage_with_adk(stage, assessment_id, run_id)

    duration_ms = int((time.time() - start_time) * 1000)

    await log_event(
        event_type=f"stage_completed_{stage}",
        user_role="system",
        assessment_id=assessment_id,
        stage=stage,
        duration_ms=duration_ms,
        meta={"runtime": settings.AGENT_RUNTIME, **stage_output},
    )

    return {
        "status": "success",
        "runtime": "local_adk",
        "stage": stage,
        "durationMs": duration_ms,
        "data": stage_output,
    }
