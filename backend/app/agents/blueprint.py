import asyncio
import json
import time
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.models import Blueprint, BlueprintCell, Assessment, Course, CLO, Topic, TypeConfig
from app.services.firestore import db
from app.services.traces import tracker
from app.tools.blueprint_rules import validate_blueprint, repair_blueprint
from app.tools.similarity import require_llm_or_fallback, get_llm_client

logger = logging.getLogger("assesscraft.blueprint")


class BlueprintResponse(BaseModel):
    cells: List[BlueprintCell]
    rationale: str = Field(description="Pedagogical rationale for the marks distribution")


async def run_blueprint_agent(assessment_id: str, run_id: Optional[str] = None) -> Blueprint:
    """
    Executes the Blueprint Agent:
    1. Reads assessment requirements, course CLOs and topics.
    2. Proposes blueprint cells via the LLM or curriculum baseline.
    3. Runs deterministic validation; repairs up to 2 times if violations occur.
    4. Writes blueprint to Firestore and traces execution in runs/{runId}.
    """
    start_time = time.time()
    assessment_data = await db.get("assessments", assessment_id)
    if not assessment_data:
        raise ValueError(f"Assessment {assessment_id} not found")

    course_id = assessment_data.get("courseId", "CS2040")
    course_data = await db.get("courses", course_id) or {}
    target_marks = assessment_data.get("totalMarks", 100)
    request_text = assessment_data.get("request", "")
    rid = run_id or assessment_data.get("runId") or f"run-bp-{assessment_id}"
    type_config = [TypeConfig(**t) for t in assessment_data.get("typeConfig") or []] or None
    q_types = assessment_data.get("qTypes") or ["mcq", "short_answer"]
    if type_config:
        type_rules = "Lecturer's question-type requirements (HARD RULES, these override the request text and the standard structure):\n" + "\n".join(
            f"- {t.qType}: exactly {t.count} questions, {t.marks // t.count} marks each ({t.marks} marks total)"
            for t in type_config
        ) + "\nUse NO other question types."
    else:
        type_rules = f"Permitted question types (use NO others): {', '.join(q_types)}"

    clos = [CLO(**c) for c in course_data.get("clos", [])]
    topics = [Topic(**t) for t in course_data.get("topics", [])]
    if not clos or not topics:
        # Without real outcomes the LLM invents CLO ids and the coverage rule passes vacuously.
        raise ValueError(f"Course {course_id} has no extracted learning outcomes/topics; extract outcomes first.")

    await tracker.record_step(
        run_id=rid,
        agent="Blueprint",
        tool="propose_blueprint",
        input_summary=f"Focus: {request_text or 'none'} | Target Marks: {target_marks} | CLOs: {len(clos)}",
        output_summary="Synthesizing assessment matrix across CLOs and Bloom cognitive levels",
        status="running",
    )

    client = get_llm_client()
    cells: List[BlueprintCell] = []
    rationale: str = ""

    # 1. Try the LLM if configured
    if client:
        try:
            with open("app/agents/prompts/blueprint.md", "r") as f:
                instruction = f.read()

            prompt = (
                f"{instruction}\n\n"
                f"Course ID: {course_id} ({course_data.get('title', 'Database Systems')})\n"
                + (f"Lecturer Topic Focus: {request_text}\n" if request_text.strip() else "")
                + f"Target Total Marks: {target_marks}\n"
                f"{type_rules}\n\n"
                f"Approved CLOs:\n" + "\n".join([f"- {c.id}: {c.text} (Bloom: {c.bloomLevel})" for c in clos]) + "\n\n"
                f"Curricular Topics:\n" + "\n".join([f"- {t.id}: {t.name} (CLOs: {', '.join(t.cloIds)})" for t in topics]) + "\n"
            )

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.LLM_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": BlueprintResponse,
                    "thinking_config": {"thinking_budget": 0},
                },
            )
            parsed = json.loads(response.text)
            cells = [BlueprintCell(**c) for c in parsed.get("cells", [])]
            rationale = parsed.get("rationale", "")
            logger.info("Blueprint generated via the LLM.")
        except Exception as e:
            logger.warning(f"LLM Blueprint generation failed ({e}); using curricular reference template.")

    # 2. Curricular Reference Baseline (Guaranteed balanced distribution for 100 marks)
    if not cells:
        require_llm_or_fallback("Blueprint agent")
        fallback_config = None
        if not type_config:
            # Legacy assessment without per-type targets: split marks across permitted types, each split evenly.
            shares = [target_marks // len(q_types)] * len(q_types)
            shares[-1] += target_marks - sum(shares)
            fallback_config = [
                TypeConfig(qType=qt, marks=m, count=next((c for c in range(min(50, m // 2), 0, -1) if m % c == 0), 1))
                for qt, m in zip(q_types, shares) if m > 0
            ]
        cells = repair_blueprint([], target_marks=target_marks, clos=clos, topics=topics, type_config=type_config or fallback_config)
        rationale = "Blueprint spread across the course's extracted learning outcomes using the requested question counts and marks."

    # 3. Deterministic Python Validation & Automated Repair Loop (Up to 2 Retries)
    is_valid, violations, totals = validate_blueprint(cells, target_marks=target_marks, clos=clos, topics=topics, type_config=type_config)
    retries = 0
    while not is_valid and retries < 2:
        logger.info(f"Blueprint validation failed with violations: {violations}. Repair attempt {retries + 1}.")
        cells = repair_blueprint(cells, target_marks=target_marks, clos=clos, topics=topics, type_config=type_config)
        is_valid, violations, totals = validate_blueprint(cells, target_marks=target_marks, clos=clos, topics=topics, type_config=type_config)
        retries += 1

    duration_ms = int((time.time() - start_time) * 1000)

    # 4. Save to Firestore
    blueprint_model = Blueprint(
        assessmentId=assessment_id,
        cells=cells,
        totals=totals,
        valid=is_valid,
        violations=violations,
        rationale=rationale,
    )
    await db.set("blueprints", assessment_id, blueprint_model.model_dump())

    # Update assessment status
    await db.update("assessments", assessment_id, {"status": "blueprint_ready"})

    # Record trace
    await tracker.record_step(
        run_id=rid,
        agent="Blueprint",
        tool="validate_blueprint",
        input_summary=f"Deterministic validation of {len(cells)} cells against target {target_marks} marks",
        output_summary=f"Validation {'PASSED (100% exact)' if is_valid else 'FAILED'}: {totals['totalMarks']} marks across {totals['totalItems']} items",
        status="completed" if is_valid else "failed",
        duration_ms=duration_ms,
        sources=[f"Course {course_id} Specification", "Academic QA Blueprint Standards"],
    )

    return blueprint_model
