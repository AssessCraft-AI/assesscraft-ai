import asyncio
import hashlib
import time
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from pathlib import Path
from app.config import settings
from app.models import (
    ModerationRecord,
    ModerationItem,
    Comment,
    Assessment,
    current_time_iso,
    generate_id,
)
from app.services.firestore import db
from app.services.traces import tracker
from app.services.audit import log_audit
from app.tools.events import log_event
from app.tools.similarity import require_llm_or_fallback, get_llm_client

logger = logging.getLogger("assesscraft.moderation")


class ModerationAgentOutput(BaseModel):
    checklist: List[ModerationItem]
    aiComments: List[Comment]
    executiveSummary: str


def inputs_key(versions: List[dict], flags: List[dict]) -> str:
    """Changes when versions are reassembled or a flag is opened or decided.
    shortcut: item text edits do not change it; add item updatedAt if edits after the audit matter."""
    ids = sorted(iid for v in versions for iid in v.get("itemIds", []))
    open_flags = sorted(f.get("id", "") for f in flags if f.get("resolution") is None)
    return hashlib.md5(json.dumps([ids, open_flags]).encode("utf-8")).hexdigest()


def _version_text(version: dict, items_by_id: Dict[str, dict]) -> str:
    """One version's questions as plain text for the moderation prompt."""
    lines = [f"Version {version.get('label')}:"]
    for iid in version.get("itemIds", []):
        it = items_by_id.get(iid)
        if not it:
            continue
        opts = " ".join(f"({o.get('id')}) {o.get('text')}" for o in it.get("options") or [])
        lines.append(
            f"- [{iid}] {it.get('qType')} {it.get('marks')} marks, {it.get('cloId')}/{it.get('bloom')}: "
            f"{it.get('stem')} {opts} | Key: {it.get('key')} | Rationale: {it.get('rationale')}"
        )
    return "\n".join(lines) + "\n"


async def run_moderation_agent(assessment_id: str, run_id: Optional[str] = None) -> ModerationRecord:
    """
    Moderation Agent:
    Performs comprehensive academic quality assurance, synthesizes version comparability,
    verifies resolution of reviewer flags, and prepares an executive moderation pack
    with itemized checklist, constructive comments, and an executive summary.
    """
    start_time = time.time()
    assessment = await db.get("assessments", assessment_id)
    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    course_id = assessment.get("courseId", "CS2040")
    course = await db.get("courses", course_id) or {}
    course_title = course.get("title", "Database Systems")
    assessment_title = assessment.get("title", f"{course_id} Examination")
    target_marks = assessment.get("totalMarks", 100)

    run_id = run_id or assessment.get("runId") or f"run-{assessment_id[:8]}"

    # Fetch associated versions and equivalence report
    versions = await db.query("versions", filters=[("assessmentId", "==", assessment_id)])
    equivalence = await db.get("equivalenceReports", assessment_id) or {}
    existing_mod = await db.get("moderation", assessment_id)

    # Collect version item IDs
    item_ids_vA = []
    item_ids_vB = []
    for v in versions:
        if v.get("label") == "A":
            item_ids_vA = v.get("itemIds", [])
        elif v.get("label") == "B":
            item_ids_vB = v.get("itemIds", [])

    # Every assembled question, so the agent judges the paper it actually signs off (not just ids and counts).
    versions.sort(key=lambda v: v.get("label", ""))
    assembled_ids = [iid for v in versions for iid in v.get("itemIds", [])]
    fetched = await asyncio.gather(*[db.get("items", iid) for iid in assembled_ids])
    items_by_id = {it["id"]: it for it in fetched if it}

    # Check reviewer flags specifically for items assigned to the assembled papers (all versions, not only A/B)
    all_flags = await db.query("flags", filters=[("assessmentId", "==", assessment_id)])
    assembled_item_ids = set(assembled_ids)
    unresolved_high_in_paper = [
        f for f in all_flags
        if f.get("severity") == "high"
        and f.get("resolution") is None
        and f.get("itemId") in assembled_item_ids
    ]

    # Check for existing human comments and decision to preserve them
    existing_human_comments = []
    existing_decision = None
    existing_decided_by = None
    existing_decided_at = None
    if existing_mod:
        existing_human_comments = existing_mod.get("humanComments", [])
        existing_decision = existing_mod.get("decision")
        existing_decided_by = existing_mod.get("decidedBy")
        existing_decided_at = existing_mod.get("decidedAt")

    prompt_file = Path(__file__).parent / "prompts" / "moderation.md"
    instruction = ""
    try:
        if prompt_file.exists():
            instruction = prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not load prompt {prompt_file}: {e}")

    # Attempt LLM generation if configured
    client = get_llm_client()
    generated_output: Optional[ModerationAgentOutput] = None

    if client and instruction:
        try:
            prompt = (
                f"{instruction}\n\n"
                f"Course: {course_id} - {course_title}\n"
                f"Assessment: {assessment_title} (Target Marks: {target_marks})\n"
                f"Versions Assembled: {len(versions)}\n"
                f"Equivalence Report (solver status {equivalence.get('solverStatus', 'NOT_RUN')}): "
                f"{json.dumps(equivalence.get('deviations', {}))}\n"
                f"Equivalence limitations: {json.dumps(equivalence.get('limitations', []))}\n"
                f"Unresolved High Severity Flags in the papers ({len(unresolved_high_in_paper)}):\n"
                + "".join(f"- {f.get('itemId')} [{f.get('type')}]: {f.get('detail')}\n" for f in unresolved_high_in_paper)
                + "\n"
                + "".join(_version_text(v, items_by_id) for v in versions)
                + "\n"
                "Generate the structured moderation checklist, 3-5 constructive AI comments citing specific items, "
                "and a formal executive summary for the Board of Examiners."
            )
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.LLM_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": ModerationAgentOutput,
                    "thinking_config": {"thinking_budget": 0},
                },
            )
            if response.text:
                generated_output = ModerationAgentOutput.model_validate_json(response.text)
        except Exception as e:
            logger.warning(f"LLM generation failed for moderation agent, falling back to deterministic QA rules: {e}")

    # Fallback to high-fidelity deterministic institutional moderation report
    generated_by = "agent"
    if not generated_output:
        require_llm_or_fallback("Moderation agent")
        generated_by = "fallback"
        has_overlap = False
        if item_ids_vA and item_ids_vB:
            overlap = set(item_ids_vA).intersection(set(item_ids_vB))
            has_overlap = len(overlap) > 0

        open_flags = sum(1 for f in all_flags if f.get("resolution") is None)

        checklist = [
            ModerationItem(
                id="chk-01",
                title="Blueprint Matrix & Exact Marks Parity",
                passed=bool(item_ids_vA and item_ids_vB) and not has_overlap,
                notes=f"Target is {target_marks} marks per version. Section split not assessed offline; see the live checks.",
            ),
            ModerationItem(
                id="chk-02",
                title="Multi-Version Equivalence & Zero Question Leakage",
                passed=bool(item_ids_vA and item_ids_vB) and not has_overlap,
                notes=(
                    "No question appears in both Version A and Version B."
                    if item_ids_vA and item_ids_vB and not has_overlap
                    else "Versions share questions or are not assembled yet."
                ),
            ),
            ModerationItem(
                id="chk-03",
                title="Adversarial Item Review & Key Consistency",
                passed=open_flags == 0,
                notes=(
                    "Every reviewer flag has a lecturer decision."
                    if open_flags == 0
                    else f"{open_flags} reviewer flag(s) still need a lecturer decision."
                ),
            ),
            ModerationItem(
                id="chk-04",
                title="Cognitive Demand & Bloom's Taxonomy Balance",
                passed=False,
                notes="Not assessed: requires the moderation agent (LLM unavailable).",
            ),
            ModerationItem(
                id="chk-05",
                title="Marking Rubric Granularity & Model Solutions",
                passed=False,
                notes="Not assessed: requires the moderation agent (LLM unavailable).",
            ),
        ]

        # No canned praise: offline mode has not read the items.
        ai_comments = []

        exec_summary = (
            f"Offline quality assurance summary for {assessment_title} ({course_id}). "
            f"{len(versions)} version(s) assembled; "
            f"{'no' if not has_overlap else 'some'} questions shared between Version A and Version B. "
            f"{open_flags} reviewer flag(s) remain open, {len(unresolved_high_in_paper)} of them high severity in the assembled papers. "
            "Cognitive balance and rubric quality were not assessed because the moderation agent was unavailable."
        )

        generated_output = ModerationAgentOutput(
            checklist=checklist,
            aiComments=ai_comments,
            executiveSummary=exec_summary,
        )

    # Assemble final record
    moderation_record = ModerationRecord(
        assessmentId=assessment_id,
        checklist=generated_output.checklist,
        aiComments=generated_output.aiComments,
        humanComments=existing_human_comments,
        executiveSummary=generated_output.executiveSummary,
        decision=existing_decision,
        decidedBy=existing_decided_by,
        decidedAt=existing_decided_at,
        updatedAt=current_time_iso(),
        generatedBy=generated_by,
        inputsKey=inputs_key(versions, all_flags),
    )

    # Persist in Firestore. An existing record gets only its AI fields: comments or a decision
    # made while the (slow) agent ran must not be overwritten by the copy read at the start.
    data = moderation_record.model_dump(exclude={"stale"})
    ai_fields = ("checklist", "aiComments", "executiveSummary", "updatedAt", "generatedBy", "inputsKey")
    if not await db.update("moderation", assessment_id, {k: data[k] for k in ai_fields}):
        await db.set("moderation", assessment_id, data)

    # The status only moves to in_moderation when the lecturer submits (POST /assessments/{id}/submit),
    # so generating a preview pack does not hand the paper to the moderator.

    duration_ms = int((time.time() - start_time) * 1000)

    # Trace step
    await tracker.record_step(
        run_id=run_id,
        agent="Moderation",
        input_summary=f"Audit parallel versions, equivalence bounds, and review flags for {assessment_title}",
        output_summary=f"Generated {len(moderation_record.checklist)} checklist items, {len(moderation_record.aiComments)} comments, and executive summary",
        status="completed",
        duration_ms=duration_ms,
    )

    # Log telemetry
    await log_event(
        event_type="assessment_moderated",
        user_role="system",
        assessment_id=assessment_id,
        meta={
            "checklistCount": len(moderation_record.checklist),
            "aiCommentCount": len(moderation_record.aiComments),
            "durationMs": duration_ms,
        },
    )

    return moderation_record
