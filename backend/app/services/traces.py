from typing import Optional, List, Dict, Any
import time
from app.services.firestore import db
from app.models import RunTrace, RunStep, generate_id, current_time_iso


class RunTracker:
    """
    Manages agent execution runs and fine-grained step recording.
    Feeds the Agent Trace drawer in the frontend.
    """
    @staticmethod
    async def create_run(
        run_id: Optional[str] = None,
        assessment_id: Optional[str] = None,
        course_id: Optional[str] = None,
        workflow: str = "assessment_generation",
    ) -> RunTrace:
        rid = run_id or generate_id()
        trace = RunTrace(
            id=rid,
            assessmentId=assessment_id,
            courseId=course_id,
            workflow=workflow,
            status="running",
            steps=[],
        )
        await db.set("runs", rid, trace.model_dump())
        return trace

    @staticmethod
    async def record_step(
        run_id: str,
        agent: str,
        input_summary: str,
        output_summary: str,
        tool: Optional[str] = None,
        sources: Optional[List[str]] = None,
        status: str = "completed",
        duration_ms: Optional[int] = None,
    ) -> RunStep:
        step = RunStep(
            agent=agent,
            tool=tool,
            input_summary=input_summary,
            output_summary=output_summary,
            sources=sources or [],
            status=status,
            endedAt=current_time_iso(),
            durationMs=duration_ms,
        )

        trace_data = await db.get("runs", run_id)
        if trace_data:
            steps = trace_data.get("steps", [])
            steps.append(step.model_dump())
            trace_data["steps"] = steps
            trace_data["updatedAt"] = current_time_iso()
            await db.set("runs", run_id, trace_data)
        else:
            trace = RunTrace(
                id=run_id,
                status="running",
                steps=[step],
            )
            await db.set("runs", run_id, trace.model_dump())

        return step

    @staticmethod
    async def complete_run(run_id: str, status: str = "completed"):
        trace_data = await db.get("runs", run_id)
        if trace_data:
            trace_data["status"] = status
            trace_data["updatedAt"] = current_time_iso()
            await db.set("runs", run_id, trace_data)


tracker = RunTracker()
