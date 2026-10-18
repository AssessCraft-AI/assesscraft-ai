from fastapi import APIRouter, HTTPException, Depends, status
from app.models import Blueprint, Assessment, CLO, Topic, TypeConfig, User
from app.tools.blueprint_rules import validate_blueprint
from app.services.firestore import db
from app.services.audit import log_audit
from app.services.traces import tracker
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.agents.orchestrator import execute_workflow_stage
from app.api.assessments import get_editable_assessment, get_visible_assessment

router = APIRouter(prefix="/assessments/{assessment_id}/blueprint", tags=["blueprints"])


@router.get("", response_model=Blueprint)
async def get_blueprint(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
):
    await get_visible_assessment(assessment_id, current_user)
    doc = await db.get("blueprints", assessment_id)
    if not doc:
        # Return empty draft blueprint structure
        return Blueprint(
            assessmentId=assessment_id,
            cells=[],
            totals={"totalMarks": 0, "targetMarks": 100},
            valid=False,
            violations=["Blueprint has not been generated yet"],
        )
    return Blueprint(**doc)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def generate_blueprint(
    assessment_id: str,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    assessment = await get_editable_assessment(assessment_id, current_user)
    course = await db.get("courses", assessment.get("courseId", "")) or {}
    if not course.get("clos") or not course.get("topics"):
        raise HTTPException(
            status_code=400,
            detail="This course has no learning outcomes yet. Upload materials and extract outcomes first.",
        )

    run_id = assessment.get("runId") or f"run-bp-{assessment_id}"
    # Runs inside the request: Cloud Run throttles CPU once a response is sent, which stalls background tasks.
    await execute_workflow_stage("blueprint", assessment_id, run_id)

    return {
        "status": "processing",
        "runId": run_id,
        "message": "Blueprint agent initiated",
    }


@router.put("", response_model=Blueprint)
async def update_blueprint(
    assessment_id: str,
    payload: Blueprint,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    assessment = await get_editable_assessment(assessment_id, current_user)

    # Never trust the client's valid/totals: the UI checks only total marks, not CLO coverage.
    course = await db.get("courses", assessment.get("courseId", "")) or {}
    payload.cells = [c for c in payload.cells if c.count > 0]  # the UI zeroes a cell to drop it
    payload.valid, payload.violations, payload.totals = validate_blueprint(
        payload.cells,
        target_marks=assessment.get("totalMarks", 100),
        clos=[CLO(**c) for c in course.get("clos", [])],
        topics=[Topic(**t) for t in course.get("topics", [])],
        type_config=[TypeConfig(**t) for t in assessment.get("typeConfig") or []] or None,
    )

    before = await db.get("blueprints", assessment_id)
    payload.assessmentId = assessment_id
    saved = await db.set("blueprints", assessment_id, payload.model_dump())

    # Update assessment status
    if payload.valid:
        await db.update("assessments", assessment_id, {"status": "blueprint_ready"})

    await log_audit(
        actor_uid=current_user.uid,
        action="update_blueprint",
        entity="blueprints",
        entity_id=assessment_id,
        before=before,
        after=saved,
    )
    await log_event(
        event_type="blueprint_updated",
        user_role=current_user.role,
        assessment_id=assessment_id,
        meta={"valid": payload.valid, "cells_count": len(payload.cells)},
    )
    return Blueprint(**saved)
